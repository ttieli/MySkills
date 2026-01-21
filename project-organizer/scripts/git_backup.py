#!/usr/bin/env python3
"""
Git 备份工具 - 在整理操作前后创建备份点。

使用方法：
  # 整理前：创建备份
  python git_backup.py before --message "整理前备份"

  # 整理后：创建检查点
  python git_backup.py after --message "整理完成"

  # 恢复到整理前状态
  python git_backup.py restore

  # 确认整理结果，清理备份
  python git_backup.py confirm

工作原理：
1. before: 创建 stash 或备份分支保存当前状态
2. after: 提交整理结果到临时提交
3. restore: 恢复到 before 状态
4. confirm: 确认无误后清理备份标记
"""

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path


BACKUP_BRANCH_PREFIX = "backup/dir-organizer"
BACKUP_TAG_PREFIX = "dir-organizer-backup"


def run_git(args: list, check: bool = True, capture: bool = True) -> tuple[bool, str]:
    """运行 git 命令"""
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=capture,
            text=True,
            check=False
        )
        if check and result.returncode != 0:
            return False, result.stderr.strip()
        return True, result.stdout.strip()
    except Exception as e:
        return False, str(e)


def is_git_repo() -> bool:
    """检查当前目录是否是 git 仓库"""
    success, _ = run_git(["rev-parse", "--git-dir"], check=False)
    return success


def has_changes() -> bool:
    """检查是否有未提交的更改"""
    success, output = run_git(["status", "--porcelain"], check=False)
    return bool(output.strip())


def get_current_branch() -> str:
    """获取当前分支名"""
    success, output = run_git(["branch", "--show-current"])
    return output if success else "HEAD"


def create_backup_tag(message: str) -> tuple[bool, str]:
    """创建备份标签"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    tag_name = f"{BACKUP_TAG_PREFIX}-{timestamp}"

    # 如果有未提交更改，先 stash
    stashed = False
    if has_changes():
        success, output = run_git(["stash", "push", "-m", f"dir-organizer backup: {message}"])
        if not success:
            return False, f"Failed to stash changes: {output}"
        stashed = True

    # 创建标签
    success, output = run_git(["tag", "-a", tag_name, "-m", message])
    if not success:
        if stashed:
            run_git(["stash", "pop"])
        return False, f"Failed to create tag: {output}"

    # 恢复 stash
    if stashed:
        run_git(["stash", "pop"])

    return True, tag_name


def cmd_before(args):
    """创建整理前备份"""
    if not is_git_repo():
        print("Error: Not a git repository", file=sys.stderr)
        return 1

    message = args.message or "整理前备份"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 方式1：如果有未跟踪的文件，先添加
    has_untracked = False
    success, status_output = run_git(["status", "--porcelain"])
    if success:
        untracked = [line for line in status_output.split("\n") if line.startswith("??")]
        if untracked:
            has_untracked = True
            print(f"发现 {len(untracked)} 个未跟踪文件")

    # 方式2：创建备份分支
    backup_branch = f"{BACKUP_BRANCH_PREFIX}-{timestamp}"
    current_branch = get_current_branch()

    # 暂存所有更改（包括未跟踪文件）
    if has_changes():
        # 添加所有文件（包括未跟踪的）
        run_git(["add", "-A"])

        # 创建临时提交
        success, output = run_git(["commit", "-m", f"[BACKUP] {message}", "--no-verify"])
        if not success:
            print(f"Warning: Could not create backup commit: {output}")
        else:
            # 创建备份分支指向这个提交
            run_git(["branch", backup_branch])

            # 撤销这个提交但保留更改
            run_git(["reset", "--mixed", "HEAD~1"])

            print(f"✓ 备份分支已创建: {backup_branch}")
            print(f"  如需恢复: git checkout {backup_branch}")
    else:
        # 没有更改，直接创建分支
        run_git(["branch", backup_branch])
        print(f"✓ 备份分支已创建: {backup_branch}")
        print("  (没有未提交的更改)")

    # 写入状态文件
    state_file = Path(".git") / "dir-organizer-state"
    state_file.write_text(f"backup_branch={backup_branch}\ncurrent_branch={current_branch}\ntimestamp={timestamp}\n")

    print(f"\n准备就绪，可以开始整理操作。")
    print(f"整理完成后运行: python git_backup.py after")
    print(f"如需恢复: python git_backup.py restore")

    return 0


def cmd_after(args):
    """整理后创建检查点"""
    if not is_git_repo():
        print("Error: Not a git repository", file=sys.stderr)
        return 1

    message = args.message or "整理完成"

    # 检查状态文件
    state_file = Path(".git") / "dir-organizer-state"
    if not state_file.exists():
        print("Warning: No 'before' backup found. Creating standalone checkpoint.")

    # 查看整理结果
    success, status = run_git(["status", "--short"])
    if success and status:
        print("整理后的更改：")
        for line in status.split("\n")[:20]:  # 最多显示20行
            print(f"  {line}")
        if len(status.split("\n")) > 20:
            print(f"  ... 还有 {len(status.split(chr(10))) - 20} 个更改")
        print()

    # 不自动提交，让用户决定
    print("整理操作已完成。")
    print()
    print("下一步：")
    print("  1. 检查上述更改是否符合预期")
    print("  2. 如果满意: python git_backup.py confirm")
    print("  3. 如需恢复: python git_backup.py restore")

    return 0


def cmd_restore(args):
    """恢复到整理前状态"""
    if not is_git_repo():
        print("Error: Not a git repository", file=sys.stderr)
        return 1

    state_file = Path(".git") / "dir-organizer-state"

    if not state_file.exists():
        print("Error: No backup state found. Cannot restore.", file=sys.stderr)
        print("Try: git stash list  或  git branch -a | grep backup")
        return 1

    # 读取状态
    state = {}
    for line in state_file.read_text().strip().split("\n"):
        if "=" in line:
            key, value = line.split("=", 1)
            state[key] = value

    backup_branch = state.get("backup_branch")
    if not backup_branch:
        print("Error: Backup branch not found in state file", file=sys.stderr)
        return 1

    # 确认
    if not args.yes:
        print(f"将恢复到备份分支: {backup_branch}")
        print("这将丢弃所有整理操作后的更改。")
        confirm = input("确认恢复？[y/N] ").strip().lower()
        if confirm != "y":
            print("已取消")
            return 0

    # 丢弃当前所有更改
    run_git(["reset", "--hard", "HEAD"])
    run_git(["clean", "-fd"])

    # 获取备份分支的内容
    success, output = run_git(["checkout", backup_branch, "--", "."])
    if not success:
        # 尝试另一种方式
        run_git(["checkout", backup_branch])
        run_git(["checkout", state.get("current_branch", "main")])

    print(f"✓ 已恢复到备份状态")

    # 清理状态文件
    state_file.unlink()

    return 0


def cmd_confirm(args):
    """确认整理结果，清理备份"""
    if not is_git_repo():
        print("Error: Not a git repository", file=sys.stderr)
        return 1

    state_file = Path(".git") / "dir-organizer-state"

    if not state_file.exists():
        print("No backup state to clean up.")
        return 0

    # 读取状态
    state = {}
    for line in state_file.read_text().strip().split("\n"):
        if "=" in line:
            key, value = line.split("=", 1)
            state[key] = value

    backup_branch = state.get("backup_branch")

    # 确认
    if not args.yes:
        print("确认整理结果后，将删除备份分支。")
        if backup_branch:
            print(f"  将删除: {backup_branch}")
        confirm = input("确认？[y/N] ").strip().lower()
        if confirm != "y":
            print("已取消")
            return 0

    # 删除备份分支
    if backup_branch:
        success, output = run_git(["branch", "-D", backup_branch])
        if success:
            print(f"✓ 已删除备份分支: {backup_branch}")
        else:
            print(f"Warning: Could not delete backup branch: {output}")

    # 清理状态文件
    state_file.unlink()
    print("✓ 备份已清理")

    return 0


def cmd_status(args):
    """显示当前备份状态"""
    if not is_git_repo():
        print("Error: Not a git repository", file=sys.stderr)
        return 1

    state_file = Path(".git") / "dir-organizer-state"

    if state_file.exists():
        print("当前有活跃的整理会话：")
        for line in state_file.read_text().strip().split("\n"):
            print(f"  {line}")
        print()
        print("操作：")
        print("  python git_backup.py restore  - 恢复到整理前")
        print("  python git_backup.py confirm  - 确认整理结果")
    else:
        print("没有活跃的整理会话")

    # 显示所有备份分支
    success, output = run_git(["branch", "-a"])
    if success:
        backup_branches = [b.strip() for b in output.split("\n")
                         if BACKUP_BRANCH_PREFIX in b]
        if backup_branches:
            print(f"\n历史备份分支：")
            for b in backup_branches:
                print(f"  {b}")

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Git 备份工具 - 整理操作前后的安全备份",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  %(prog)s before                    # 整理前创建备份
  %(prog)s after                     # 整理后创建检查点
  %(prog)s restore                   # 恢复到整理前
  %(prog)s confirm                   # 确认整理，清理备份
  %(prog)s status                    # 查看备份状态
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # before
    p_before = subparsers.add_parser("before", help="创建整理前备份")
    p_before.add_argument("-m", "--message", help="备份说明")

    # after
    p_after = subparsers.add_parser("after", help="整理后创建检查点")
    p_after.add_argument("-m", "--message", help="说明")

    # restore
    p_restore = subparsers.add_parser("restore", help="恢复到整理前")
    p_restore.add_argument("-y", "--yes", action="store_true", help="跳过确认")

    # confirm
    p_confirm = subparsers.add_parser("confirm", help="确认整理，清理备份")
    p_confirm.add_argument("-y", "--yes", action="store_true", help="跳过确认")

    # status
    subparsers.add_parser("status", help="查看备份状态")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    commands = {
        "before": cmd_before,
        "after": cmd_after,
        "restore": cmd_restore,
        "confirm": cmd_confirm,
        "status": cmd_status,
    }

    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
