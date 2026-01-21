#!/usr/bin/env python3
"""
安全执行器 - 执行 Claude 生成的整理计划。

职责：
- 接收 Claude 生成的标准化 plan.json
- 事务日志记录
- 原子操作（复制→验证→删除）
- 自动生成回滚脚本

不负责：
- 分类决策（由 Claude 完成）
- 用户交互确认（由 Claude 完成）

命令：
  execute       执行计划
  verify        验证会话
  cleanup       清理源文件
  rollback      显示回滚信息
  list-sessions 列出所有会话
"""

import argparse
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# 添加当前目录到路径以导入本地模块
sys.path.insert(0, str(Path(__file__).parent))

from transaction_log import (
    TransactionLog, Operation, OperationStatus, OperationType,
    calculate_dir_checksum, verify_copy, rsync_copy
)


# ============ 受保护路径（最后一道防线） ============

ABSOLUTE_PROTECTED = {
    "/System", "/bin", "/sbin", "/usr", "/etc", "/var", "/opt",
    "/Library", "/Applications", "/Volumes", "/private",
}

USER_PROTECTED = {
    ".ssh", ".gnupg", ".config", ".local",
    ".pyenv", ".asdf", ".nvm", ".rbenv", ".cargo", ".rustup",
    "Library",  # ~/Library
}


def is_protected(path: Path) -> tuple[bool, str]:
    """
    最后一道安全检查。即使 Claude 的计划中包含了这些路径，也拒绝执行。
    """
    path_str = str(path.resolve())
    home = Path.home()

    # 系统路径
    for protected in ABSOLUTE_PROTECTED:
        if path_str.startswith(protected):
            return True, f"System path: {protected}"

    # 用户关键路径
    try:
        rel = path.relative_to(home)
        first_part = rel.parts[0] if rel.parts else ""
        if first_part in USER_PROTECTED:
            return True, f"User protected: {first_part}"
    except ValueError:
        pass

    return False, ""


# ============ 计划验证 ============

def validate_plan(plan: Dict) -> tuple[bool, List[str]]:
    """
    验证计划格式和安全性。

    Returns:
        (valid, errors)
    """
    errors = []

    # 版本检查
    if "version" not in plan:
        errors.append("Missing 'version' field")

    # 操作列表
    if "operations" not in plan:
        errors.append("Missing 'operations' field")
    else:
        for i, op in enumerate(plan["operations"]):
            # 必需字段
            for field in ["id", "action", "source", "target"]:
                if field not in op:
                    errors.append(f"Operation {i}: missing '{field}'")

            # 安全检查
            if "source" in op:
                source = Path(op["source"]).expanduser()
                is_prot, reason = is_protected(source)
                if is_prot:
                    errors.append(f"Operation {op.get('id', i)}: source is protected ({reason})")

            # action 类型
            if op.get("action") not in ("move", "copy"):
                errors.append(f"Operation {op.get('id', i)}: invalid action '{op.get('action')}'")

    return len(errors) == 0, errors


# ============ 命令实现 ============

def cmd_execute(args):
    """执行计划"""
    plan_file = Path(args.plan).expanduser()
    if not plan_file.exists():
        print(f"Error: Plan file not found: {plan_file}", file=sys.stderr)
        return 1

    with open(plan_file) as f:
        plan = json.load(f)

    # 验证计划
    valid, errors = validate_plan(plan)
    if not valid:
        print("Plan validation failed:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    # 创建会话
    txlog = TransactionLog()
    txlog.session.target_root = plan.get("target_root", str(Path.home()))

    # 复制计划到会话目录
    plan_copy = txlog.session_dir / "plan.json"
    shutil.copy(plan_file, plan_copy)

    print(f"Session ID: {txlog.session_id}")
    print(f"Operations: {len(plan['operations'])}")
    print()

    # 确认执行
    if not args.yes:
        confirm = input("Proceed with execution? [y/N] ").strip().lower()
        if confirm != "y":
            print("Aborted.")
            return 0

    # 注册所有操作
    for op_dict in plan["operations"]:
        op = Operation(
            id=op_dict["id"],
            op_type=op_dict["action"],
            source=str(Path(op_dict["source"]).expanduser()),
            target=str(Path(op_dict["target"]).expanduser()),
            size_kb=op_dict.get("size_kb"),
            reason=op_dict.get("reason", ""),
        )
        txlog.add_operation(op)

    # 执行操作
    success_count = 0
    fail_count = 0

    for op_dict in plan["operations"]:
        op = txlog.get_operation(op_dict["id"])
        if not op:
            continue

        source = Path(op.source)
        target = Path(op.target)

        print(f"[{op.id}] {source.name} → {target}")

        # 最后一道安全检查
        is_prot, reason = is_protected(source)
        if is_prot:
            print(f"  ⛔ BLOCKED: {reason}")
            txlog.update_operation_status(op.id, OperationStatus.FAILED, error=reason)
            fail_count += 1
            continue

        # 检查源是否存在
        if not source.exists():
            print(f"  ✗ Source not found")
            txlog.update_operation_status(op.id, OperationStatus.FAILED, error="Source not found")
            fail_count += 1
            continue

        # 更新状态为 COPYING
        txlog.update_operation_status(op.id, OperationStatus.COPYING)

        # 计算源校验和
        source_checksum = calculate_dir_checksum(source)
        txlog.set_checksum(op.id, source_checksum=source_checksum)

        # 确保目标目录存在
        target.parent.mkdir(parents=True, exist_ok=True)

        # 执行复制
        success, output = rsync_copy(source, target)

        if not success:
            print(f"  ✗ Copy failed: {output}")
            txlog.update_operation_status(op.id, OperationStatus.FAILED, error=output)
            fail_count += 1
            continue

        # 更新状态为 COPIED
        txlog.update_operation_status(op.id, OperationStatus.COPIED)

        # 验证
        verify_success, verify_msg = verify_copy(source, target)
        target_checksum = calculate_dir_checksum(target)
        txlog.set_checksum(op.id, target_checksum=target_checksum)

        if verify_success:
            print(f"  ✓ OK")
            txlog.update_operation_status(op.id, OperationStatus.VERIFIED)
            success_count += 1
        else:
            print(f"  ⚠ Copied but verify warning: {verify_msg}")
            success_count += 1

    # 生成回滚脚本
    generate_rollback_script(txlog)

    print()
    print("=" * 60)
    print(f"Execution complete")
    print(f"  Success: {success_count}")
    print(f"  Failed: {fail_count}")
    print()
    print(f"Session ID: {txlog.session_id}")
    print(f"Rollback script: {txlog.rollback_file}")
    print()

    if fail_count > 0:
        print("Some operations failed. Source files unchanged for failed operations.")
        return 1

    print("Source files are still intact.")
    print(f"To delete sources: python {Path(__file__).name} cleanup -s {txlog.session_id}")
    print(f"To rollback: bash {txlog.rollback_file}")

    return 0


def cmd_verify(args):
    """验证会话"""
    try:
        txlog = TransactionLog(args.session)
    except FileNotFoundError:
        print(f"Session not found: {args.session}", file=sys.stderr)
        return 1

    print(f"Verifying session: {args.session}")
    print()

    all_ok = True
    for op in txlog.session.operations:
        source = Path(op.source)
        target = Path(op.target)

        print(f"[{op.id}] {source.name}")
        print(f"  Status: {op.status}")

        if op.status in (OperationStatus.COPIED.value, OperationStatus.VERIFIED.value):
            success, msg = verify_copy(source, target)
            if success:
                print(f"  ✓ {msg}")
            else:
                print(f"  ✗ {msg}")
                all_ok = False
        elif op.status == OperationStatus.FAILED.value:
            print(f"  ✗ Failed: {op.error}")
            all_ok = False
        print()

    return 0 if all_ok else 1


def cmd_cleanup(args):
    """清理源文件"""
    try:
        txlog = TransactionLog(args.session)
    except FileNotFoundError:
        print(f"Session not found: {args.session}", file=sys.stderr)
        return 1

    candidates = txlog.get_cleanup_candidates()

    if not candidates:
        print("No items to clean up.")
        return 0

    print(f"Found {len(candidates)} items to clean up:")
    total_size = 0
    for op in candidates:
        size_str = format_size(op.size_kb) if op.size_kb else "?"
        print(f"  - {op.source} ({size_str})")
        total_size += op.size_kb or 0

    print()
    print(f"Total: {format_size(total_size)}")

    if not args.force:
        print()
        print("⚠️  WARNING: This will permanently delete source files.")
        print("   Rollback will NOT be possible after this.")
        confirm = input("Delete these files? [y/N] ").strip().lower()
        if confirm != "y":
            print("Aborted.")
            return 0

    success = 0
    failed = 0

    for op in candidates:
        source = Path(op.source)
        print(f"Deleting {source}...")

        try:
            if source.is_dir():
                shutil.rmtree(source)
            elif source.exists():
                source.unlink()
            txlog.update_operation_status(op.id, OperationStatus.CLEANED)
            print(f"  ✓ Deleted")
            success += 1
        except Exception as e:
            print(f"  ✗ Failed: {e}")
            failed += 1

    print()
    print(f"Cleanup complete: {success} deleted, {failed} failed")

    return 0 if failed == 0 else 1


def cmd_rollback(args):
    """显示回滚信息"""
    try:
        txlog = TransactionLog(args.session)
    except FileNotFoundError:
        print(f"Session not found: {args.session}", file=sys.stderr)
        return 1

    rollback_file = txlog.rollback_file

    if rollback_file.exists():
        print(f"Rollback script: {rollback_file}")
        print()
        print("To execute rollback:")
        print(f"  bash {rollback_file}")
        print()

    # 检查是否已清理
    cleaned = [op for op in txlog.session.operations
               if op.status == OperationStatus.CLEANED.value]
    if cleaned:
        print(f"⚠️  WARNING: {len(cleaned)} sources already deleted.")
        print("   Full rollback may not be possible.")
        print()

    reversible = txlog.get_reversible_operations()
    if reversible:
        print(f"Reversible operations: {len(reversible)}")
        for op in reversible:
            print(f"  - {op.target} → {op.source}")

    return 0


def cmd_list_sessions(args):
    """列出所有会话"""
    sessions = TransactionLog.list_sessions()

    if not sessions:
        print("No sessions found.")
        return 0

    print(f"{'Session ID':<20} {'Created':<20} {'Status':<10} {'Ops':<5} {'Rollback'}")
    print("-" * 70)

    for s in sessions:
        created = s["created_at"][:19] if s["created_at"] else "N/A"
        rollback = "Yes" if s["has_rollback"] else "No"
        print(f"{s['session_id']:<20} {created:<20} {s['status']:<10} {s['operation_count']:<5} {rollback}")

    return 0


# ============ 工具函数 ============

def format_size(kb: int) -> str:
    """格式化文件大小"""
    if kb is None:
        return "N/A"
    if kb < 1024:
        return f"{kb}K"
    mb = kb / 1024
    if mb < 1024:
        return f"{mb:.1f}M"
    gb = mb / 1024
    return f"{gb:.1f}G"


def generate_rollback_script(txlog: TransactionLog) -> None:
    """生成回滚脚本"""
    script_lines = [
        "#!/bin/bash",
        "# Auto-generated rollback script",
        f"# Session: {txlog.session_id}",
        f"# Generated: {datetime.now().isoformat()}",
        "#",
        "# This script will restore files from target back to source.",
        "# Run this if you need to undo the organization.",
        "",
        "set -e",
        "",
        f'echo "Rolling back session {txlog.session_id}..."',
        'echo ""',
        "",
    ]

    reversible = txlog.get_reversible_operations()

    for i, op in enumerate(reversed(reversible), 1):
        source = op.source
        target = op.target

        script_lines.extend([
            f"# [{i}/{len(reversible)}] Restore: {Path(source).name}",
            f'echo "[{i}/{len(reversible)}] Restoring {Path(source).name}..."',
            f'if [ -e "{target}" ]; then',
            f'  rsync -avh "{target}/" "{source}/"',
            f'  rm -rf "{target}"',
            f'  echo "  ✓ Restored"',
            f'else',
            f'  echo "  ⚠ Target not found: {target}"',
            f'fi',
            "",
        ])

    script_lines.extend([
        'echo ""',
        'echo "Rollback complete."',
        'echo "Please verify manually:"',
        'echo "  - Check that restored files are intact"',
        'echo "  - Test any affected applications"',
        'echo "  - Remove empty directories if needed"',
    ])

    with open(txlog.rollback_file, "w") as f:
        f.write("\n".join(script_lines))

    os.chmod(txlog.rollback_file, 0o755)


# ============ 主入口 ============

def main():
    parser = argparse.ArgumentParser(
        description="安全执行器 - 执行 Claude 生成的整理计划",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s execute -p plan.json           # 执行计划
  %(prog)s verify -s 20240119_143022      # 验证会话
  %(prog)s cleanup -s 20240119_143022     # 清理源文件
  %(prog)s rollback -s 20240119_143022    # 显示回滚信息
  %(prog)s list-sessions                  # 列出所有会话
        """
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # execute
    p_exec = subparsers.add_parser("execute", help="Execute a plan")
    p_exec.add_argument("--plan", "-p", required=True, help="Plan JSON file (generated by Claude)")
    p_exec.add_argument("--yes", "-y", action="store_true", help="Skip confirmation")

    # verify
    p_verify = subparsers.add_parser("verify", help="Verify session")
    p_verify.add_argument("--session", "-s", required=True, help="Session ID")

    # cleanup
    p_clean = subparsers.add_parser("cleanup", help="Clean up source files")
    p_clean.add_argument("--session", "-s", required=True, help="Session ID")
    p_clean.add_argument("--force", "-f", action="store_true", help="Skip confirmation")

    # rollback
    p_rollback = subparsers.add_parser("rollback", help="Show rollback info")
    p_rollback.add_argument("--session", "-s", required=True, help="Session ID")

    # list-sessions
    subparsers.add_parser("list-sessions", help="List all sessions")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    commands = {
        "execute": cmd_execute,
        "verify": cmd_verify,
        "cleanup": cmd_cleanup,
        "rollback": cmd_rollback,
        "list-sessions": cmd_list_sessions,
    }

    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
