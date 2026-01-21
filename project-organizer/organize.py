#!/usr/bin/env python3
"""
项目整理便捷入口 - 可从任意目录直接调用

使用方法：
  python3 ~/.claude/skills/project-organizer/organize.py           # 分析当前目录
  python3 ~/.claude/skills/project-organizer/organize.py scan      # 扫描分析
  python3 ~/.claude/skills/project-organizer/organize.py backup    # 创建备份
  python3 ~/.claude/skills/project-organizer/organize.py restore   # 恢复备份
  python3 ~/.claude/skills/project-organizer/organize.py confirm   # 确认整理
"""

import os
import sys
from pathlib import Path

# 获取脚本所在目录
SKILL_DIR = Path(__file__).parent.resolve()
SCRIPTS_DIR = SKILL_DIR / "scripts"


def main():
    args = sys.argv[1:]

    if not args or args[0] == "scan":
        # 默认：扫描分析
        script = SCRIPTS_DIR / "root_inventory.py"
        scan_args = args[1:] if args and args[0] == "scan" else args

        # 如果没有指定 --target，使用当前工作目录
        if "--target" not in scan_args and "-t" not in scan_args:
            scan_args = ["--target", os.getcwd()] + list(scan_args)

        # 默认深度为 2
        if "--depth" not in scan_args and "-d" not in scan_args:
            scan_args = ["--depth", "2"] + list(scan_args)

        os.execvp(sys.executable, [sys.executable, str(script)] + list(scan_args))

    elif args[0] == "backup":
        # 创建备份
        script = SCRIPTS_DIR / "git_backup.py"
        backup_args = ["before"] + args[1:]
        os.execvp(sys.executable, [sys.executable, str(script)] + backup_args)

    elif args[0] == "restore":
        # 恢复备份
        script = SCRIPTS_DIR / "git_backup.py"
        restore_args = ["restore"] + args[1:]
        os.execvp(sys.executable, [sys.executable, str(script)] + restore_args)

    elif args[0] == "confirm":
        # 确认整理
        script = SCRIPTS_DIR / "git_backup.py"
        confirm_args = ["confirm"] + args[1:]
        os.execvp(sys.executable, [sys.executable, str(script)] + confirm_args)

    elif args[0] == "status":
        # 备份状态
        script = SCRIPTS_DIR / "git_backup.py"
        os.execvp(sys.executable, [sys.executable, str(script), "status"])

    elif args[0] == "help" or args[0] == "--help" or args[0] == "-h":
        print(__doc__)
        print("\n命令：")
        print("  scan [options]  扫描分析项目结构（默认）")
        print("  backup          创建 Git 备份")
        print("  restore         恢复到备份状态")
        print("  confirm         确认整理结果，清理备份")
        print("  status          查看备份状态")
        print("\n扫描选项：")
        print("  --target, -t    指定目标目录（默认：当前目录）")
        print("  --depth, -d     扫描深度（默认：2）")
        print("  --json, -j      输出 JSON 格式")
        print("  --verbose, -v   显示详细列表")

    else:
        print(f"未知命令: {args[0]}", file=sys.stderr)
        print("使用 'help' 查看可用命令", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
