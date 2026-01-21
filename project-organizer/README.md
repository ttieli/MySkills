# Project Organizer

智能项目整理工具 - 分析项目性质，规划目录结构，整理散落文件，清理重复文件。

## 接口规范 (API Contract)

> **版本**: 1.0.0
> **兼容性承诺**: 以下公共接口保持向后兼容，内部实现可能变更

### 主入口

```bash
python3 ~/.claude/skills/project-organizer/organize.py [command] [options]
```

### 命令接口

| 命令 | 说明 | 输入 | 输出 |
|------|------|------|------|
| `scan` | 扫描分析（默认） | 目录路径 | 结构化分析报告 |
| `backup` | 创建 Git 备份 | 无 | 备份分支名 |
| `restore` | 恢复到备份状态 | 无 | 恢复确认 |
| `confirm` | 确认整理结果 | 无 | 清理确认 |
| `status` | 查看备份状态 | 无 | 会话状态 |
| `help` | 显示帮助 | 无 | 帮助文本 |

### scan 命令

**输入参数**:
```bash
organize.py scan [options]

Options:
  --target, -t PATH    目标目录（默认：当前目录）
  --depth, -d N        扫描深度（默认：2）
  --json, -j           输出 JSON 格式
  --verbose, -v        显示详细列表
```

**输出格式** (文本模式):
```
Inventory for: /path/to/project
Directory type: project|home|workspace|generic
Project types: git-repo, python, node, ...

📄 散落文件（建议移动）
----------------------------------------
  → suggested_dir/ [✓|?]
      filename.ext                          SIZE

🔄 重复文件（建议删除）
----------------------------------------
  → containing_dir/
      duplicate_file                        SIZE
      [原文件: original_file]

========================================
整理建议汇总:
  • N 个文件建议移动到正确目录
  • N 个重复文件建议删除

Total: N items, SIZE
```

**输出格式** (JSON 模式):
```json
{
  "path": "/path/to/project",
  "type": "project",
  "project_types": ["git-repo", "python"],
  "scattered_files": [
    {
      "file": "filename.ext",
      "current_dir": ".",
      "suggested_dir": "notebooks/",
      "size": 1234,
      "original_exists": true
    }
  ],
  "duplicate_files": [
    {
      "file": "file 2.py",
      "original": "file.py",
      "dir": "src/",
      "size": 5678
    }
  ],
  "summary": {
    "total_items": 28,
    "total_size": 345600000,
    "scattered_count": 5,
    "duplicate_count": 3
  }
}
```

### backup 命令

**输入**: 无参数（在项目目录内运行）

**输出**:
```
✓ 备份分支已创建: backup/dir-organizer-YYYYMMDD_HHMMSS
```

**退出码**:
- `0`: 成功
- `1`: 非 Git 仓库或创建失败

### restore 命令

**输入**:
```bash
organize.py restore [-y]  # -y 跳过确认
```

**输出**:
```
✓ 已恢复到备份状态: backup/dir-organizer-YYYYMMDD_HHMMSS
```

### confirm 命令

**输入**: 无参数

**输出**:
```
✓ 整理已确认，备份分支已删除
```

### status 命令

**输入**: 无参数

**输出** (有活跃会话):
```
当前有活跃的整理会话：
  backup_branch=backup/dir-organizer-YYYYMMDD_HHMMSS
  created_at=YYYY-MM-DD HH:MM:SS
```

**输出** (无活跃会话):
```
没有活跃的整理会话
```

## 目录类型识别

| 类型 | 标识符 | 特征 |
|------|--------|------|
| 主目录 | `home` | 路径为 `~` 或包含 Desktop/Documents/Downloads |
| 项目目录 | `project` | 包含 `.git`、`package.json`、`pyproject.toml` 等 |
| 工作区 | `workspace` | 包含多个子项目 |
| 普通目录 | `generic` | 其他 |

## 项目类型标签

| 标签 | 特征文件 |
|------|----------|
| `git-repo` | `.git/` |
| `python` | `pyproject.toml`, `setup.py`, `requirements.txt` |
| `node` | `package.json` |
| `rust` | `Cargo.toml` |
| `go` | `go.mod` |
| `make` | `Makefile` |

## 散落文件分类规则

| 文件模式 | 建议目录 |
|----------|----------|
| `*.ipynb` | `notebooks/` |
| `*.sh` (非标准位置) | `scripts/` |
| `test*.png`, `*_test.jpg` | `tests/images/` |
| `output*.png`, `result*.jpg` | `output/` |

## 重复文件模式

| 模式 | 示例 | 来源 |
|------|------|------|
| `* 2.*` | `file 2.py` | macOS Finder 复制 |
| `* 3.*` | `file 3.py` | 多次复制 |
| `*副本*` | `文件副本.txt` | 中文系统 |
| `*copy*` | `file copy.py` | 手动复制 |

## 安全保障

1. **Git 备份**: 所有操作前自动创建备份分支
2. **受保护路径**: `.git/`, `src/`, `tests/`, 配置文件不动
3. **用户确认**: 删除操作需要明确确认

## 变更日志

### v1.0.0 (2026-01-20)
- 初始版本
- 定义公共接口规范
- 添加 organize.py 便捷入口
- 修复路径依赖问题
