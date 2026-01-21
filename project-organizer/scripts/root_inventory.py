#!/usr/bin/env python3
"""
目录整理工具 - 用于规划项目结构整理。

核心目标：让项目结构更整齐，而非清理空间。

功能：
1. 散落文件检测 - 找出放错位置的文件
2. 结构建议 - 推荐标准目录结构
3. 重复文件检测 - 找出 macOS 复制产生的重复文件
4. 可清理项识别 - 标记可删除的临时文件（非主要目标）

支持模式：
- 项目目录模式：整理单个项目的结构
- 工作区模式：整理多项目工作区
- 主目录模式：整理用户主目录

特性：
- 支持深度控制的递归扫描
- 自动识别目录和项目类型
- 跨平台兼容（macOS/Linux/Windows）
- 无破坏性操作
"""

import argparse
import json
import os
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Set


# ============ 跨平台体积计算 ============

def get_size_native(path: Path, max_depth: int = 10) -> Optional[int]:
    """使用 Python 原生方法计算大小（KB）"""
    try:
        if path.is_file():
            return path.stat().st_size // 1024

        total = 0
        for root, dirs, files in os.walk(path):
            depth = len(Path(root).relative_to(path).parts)
            if depth > max_depth:
                dirs.clear()
                continue

            for f in files:
                try:
                    fp = Path(root) / f
                    total += fp.stat().st_size
                except (OSError, IOError):
                    pass

        return total // 1024
    except Exception:
        return None


def get_size_du(path: Path) -> Optional[int]:
    """使用 du 命令计算大小（KB）- Unix only"""
    try:
        result = subprocess.run(
            ["du", "-sk", str(path)],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0:
            return int(result.stdout.split()[0])
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
        pass
    return None


def get_size(path: Path) -> Optional[int]:
    """跨平台获取文件/目录大小（KB）"""
    system = platform.system()
    if system in ("Darwin", "Linux"):
        size = get_size_du(path)
        if size is not None:
            return size
    return get_size_native(path)


# ============ 目录类型识别 ============

# 项目标识文件
PROJECT_MARKERS = {
    # Node.js
    "package.json": "nodejs",
    "package-lock.json": "nodejs",
    "yarn.lock": "nodejs",
    "pnpm-lock.yaml": "nodejs",
    # Python
    "pyproject.toml": "python",
    "setup.py": "python",
    "requirements.txt": "python",
    "Pipfile": "python",
    "poetry.lock": "python",
    # Rust
    "Cargo.toml": "rust",
    # Go
    "go.mod": "golang",
    # Java/Kotlin
    "pom.xml": "java",
    "build.gradle": "java",
    "build.gradle.kts": "kotlin",
    # Ruby
    "Gemfile": "ruby",
    # PHP
    "composer.json": "php",
    # .NET
    "*.csproj": "dotnet",
    "*.fsproj": "dotnet",
    # 通用
    ".git": "git-repo",
    "Makefile": "make",
    "CMakeLists.txt": "cmake",
    "Dockerfile": "docker",
}

# 主目录标识
HOME_MARKERS = {"Desktop", "Documents", "Downloads", "Pictures", "Movies", "Music", "Library"}

# 可清理项分类
CLEANABLE_PATTERNS = {
    # 构建产物
    "build_artifacts": {
        "dirs": {"dist", "build", "out", "output", "target", ".next", ".nuxt", ".output", "__pycache__", ".pytest_cache", "htmlcov", "coverage", ".tox", ".mypy_cache", ".ruff_cache"},
        "files": {"*.pyc", "*.pyo", "*.class", "*.o", "*.obj"},
        "dir_patterns": {"*.egg-info"},  # 通配符目录模式
        "description": "构建产物/缓存",
        "risk": "low",
        "rebuild": True,
    },
    # 依赖缓存
    "dependencies": {
        "dirs": {"node_modules", ".venv", "venv", "vendor", ".bundle", "Pods"},
        "description": "依赖缓存",
        "risk": "low",
        "rebuild": True,
    },
    # 日志/临时
    "logs_temp": {
        "dirs": {"logs", "log", "tmp", "temp", ".tmp", ".temp"},
        "files": {"*.log", "*.tmp"},
        "description": "日志/临时文件",
        "risk": "low",
        "rebuild": False,
    },
    # IDE 缓存
    "ide_cache": {
        "dirs": {".idea", ".vscode", ".vs"},
        "description": "IDE 配置/缓存",
        "risk": "medium",
        "rebuild": True,
    },
    # 系统生成文件
    "system_files": {
        "files": {".DS_Store", "Thumbs.db", "desktop.ini", "._.DS_Store"},
        "dirs": {"__MACOSX"},
        "description": "系统生成文件",
        "risk": "low",
        "rebuild": False,
    },
    # macOS 重复文件（复制产生的 "xxx 2.py" 等）
    "duplicates": {
        "file_patterns": {"* 2.*", "* 3.*", "* 2", "* 3", "*副本*", "*copy*"},
        "description": "疑似重复文件",
        "risk": "medium",
        "rebuild": False,
    },
}

# 需谨慎处理
CAUTION_PATTERNS = {
    "data": {"dirs": {"data", "datasets", "db"}, "description": "数据文件"},
    "models": {"files": {"*.h5", "*.pt", "*.onnx", "*.pkl", "*.model"}, "dirs": {"models", "checkpoints"}, "description": "模型文件"},
    "config": {"files": {".env", "*.conf", "*.ini"}, "dirs": {"config", "configs"}, "description": "配置文件"},
    "backup": {"dirs": {"backup", "backups", "*_backup", "*_bak"}, "files": {"*.bak", "*.backup"}, "description": "备份"},
}

# 绝对保护
PROTECTED_PATTERNS = {
    "source": {"dirs": {"src", "lib", "app", "pkg", "internal", "cmd"}},
    "tests": {"dirs": {"tests", "test", "spec", "__tests__"}},
    "docs": {"dirs": {"docs", "doc", "documentation"}},
    "vcs": {"dirs": {".git", ".svn", ".hg"}},
}

# ============ 散落文件检测（项目整理核心） ============

# 文件类型 -> 建议目录
MISPLACED_PATTERNS = {
    # Jupyter Notebooks 散落在根目录
    "notebooks": {
        "extensions": {".ipynb"},
        "suggested_dir": "notebooks",
        "description": "Jupyter notebook 散落在根目录",
        "action": "move",
    },
    # 测试相关图片散落在根目录
    "test_images": {
        "patterns": {"test*.png", "test*.jpg", "*_test.png", "*_test.jpg", "wikipedia_test*"},
        "suggested_dir": "tests/images",
        "description": "测试图片散落在根目录",
        "action": "move",
    },
    # 输出图片散落在根目录
    "output_images": {
        "patterns": {"output*.png", "output*.jpg", "result*.png", "result*.jpg"},
        "suggested_dir": "output",
        "description": "输出图片散落在根目录",
        "action": "move",
    },
    # Shell 脚本散落在根目录（非标准脚本）
    "scripts": {
        "extensions": {".sh"},
        "exclude": {"install.sh", "setup.sh", "build.sh", "run.sh", "start.sh"},
        "suggested_dir": "scripts",
        "description": "脚本文件散落在根目录",
        "action": "move",
    },
    # skill 文件散落在根目录
    "skill_files": {
        "extensions": {".skill"},
        "suggested_dir": "skills",
        "description": "skill 文件散落在根目录",
        "action": "move",
    },
}

# 标准项目目录结构建议
STANDARD_STRUCTURE = {
    "python": {
        "recommended": ["src", "tests", "docs", "scripts", "examples"],
        "optional": ["notebooks", "data", "models", "output"],
    },
    "nodejs": {
        "recommended": ["src", "tests", "docs"],
        "optional": ["scripts", "examples", "public", "assets"],
    },
    "generic": {
        "recommended": ["src", "tests", "docs"],
        "optional": ["scripts", "examples", "output"],
    },
}


def detect_misplaced_files(items: List[Dict], project_types: List[str]) -> List[Dict]:
    """
    检测散落/放错位置的文件。

    Returns:
        [
            {
                "file": "BlogTest.ipynb",
                "category": "notebooks",
                "description": "Jupyter notebook 散落在根目录",
                "suggested_dir": "notebooks",
                "action": "move",
            },
            ...
        ]
    """
    misplaced = []

    # 只检查根目录（depth=0）的文件
    root_files = [i for i in items if i["depth"] == 0 and i["type"] == "file"]
    existing_dirs = {i["name"] for i in items if i["depth"] == 0 and i["type"] == "dir"}

    for item in root_files:
        name = item["name"]
        name_lower = name.lower()

        for category, patterns in MISPLACED_PATTERNS.items():
            matched = False

            # 扩展名匹配
            if "extensions" in patterns:
                ext = Path(name).suffix.lower()
                if ext in patterns["extensions"]:
                    # 检查排除列表
                    if "exclude" in patterns and name_lower in {e.lower() for e in patterns["exclude"]}:
                        continue
                    matched = True

            # 模式匹配
            if "patterns" in patterns:
                for pattern in patterns["patterns"]:
                    if match_pattern(name, pattern):
                        matched = True
                        break

            if matched:
                # 检查建议目录是否已存在
                suggested = patterns["suggested_dir"]
                base_dir = suggested.split("/")[0]
                dir_exists = base_dir in existing_dirs

                misplaced.append({
                    "file": name,
                    "path": item.get("path", name),
                    "size_kb": item.get("size_kb", 0),
                    "category": category,
                    "description": patterns["description"],
                    "suggested_dir": suggested,
                    "dir_exists": dir_exists,
                    "action": patterns["action"],
                })
                break

    return misplaced


def detect_duplicate_files(items: List[Dict]) -> List[Dict]:
    """
    检测重复文件（macOS 复制产生的 "xxx 2.py" 等）。

    Returns:
        [
            {
                "duplicate": "debug_heading 2.py",
                "original": "debug_heading.py",
                "original_exists": True,
                "location": "tests/",
            },
            ...
        ]
    """
    duplicates = []

    # 收集所有文件
    all_files = {}
    for item in items:
        if item["type"] == "file":
            rel_path = item.get("relative_path", item["name"])
            dir_path = str(Path(rel_path).parent) if "/" in rel_path else ""
            all_files[(dir_path, item["name"])] = item

    # 检测重复模式
    duplicate_patterns = [
        (r" 2(\.[^.]+)?$", ""),  # "file 2.py" -> "file.py"
        (r" 3(\.[^.]+)?$", ""),
        (r"副本(\.[^.]+)?$", ""),
        (r" copy(\.[^.]+)?$", ""),
    ]

    import re

    for (dir_path, name), item in all_files.items():
        for pattern, replacement in duplicate_patterns:
            match = re.search(pattern, name, re.IGNORECASE)
            if match:
                # 构建原始文件名
                original_name = re.sub(pattern, match.group(1) or "", name, flags=re.IGNORECASE)
                if not original_name:
                    continue

                original_exists = (dir_path, original_name) in all_files

                duplicates.append({
                    "duplicate": name,
                    "path": item.get("relative_path", name),
                    "size_kb": item.get("size_kb", 0),
                    "original": original_name,
                    "original_exists": original_exists,
                    "location": dir_path or "(root)",
                })
                break

    return duplicates


def suggest_structure(items: List[Dict], project_types: List[str]) -> Dict:
    """
    根据项目类型建议目录结构改进。

    Returns:
        {
            "missing_recommended": ["scripts"],
            "missing_optional": ["notebooks", "examples"],
            "suggestions": [
                "建议创建 scripts/ 目录存放脚本文件",
                ...
            ]
        }
    """
    existing_dirs = {i["name"].lower() for i in items if i["depth"] == 0 and i["type"] == "dir"}

    # 选择项目类型的标准结构
    proj_type = "generic"
    if "python" in project_types:
        proj_type = "python"
    elif "nodejs" in project_types:
        proj_type = "nodejs"

    structure = STANDARD_STRUCTURE.get(proj_type, STANDARD_STRUCTURE["generic"])

    missing_recommended = [d for d in structure["recommended"] if d.lower() not in existing_dirs]
    missing_optional = [d for d in structure["optional"] if d.lower() not in existing_dirs]

    suggestions = []

    # 根据散落文件生成建议
    root_files = [i for i in items if i["depth"] == 0 and i["type"] == "file"]

    # 检查是否有 notebooks 散落
    has_notebooks = any(Path(f["name"]).suffix.lower() == ".ipynb" for f in root_files)
    if has_notebooks and "notebooks" not in existing_dirs:
        suggestions.append("有 Jupyter notebook 散落在根目录，建议创建 notebooks/ 目录整理")

    # 检查是否有脚本散落
    has_scripts = any(Path(f["name"]).suffix.lower() == ".sh" for f in root_files)
    if has_scripts and "scripts" not in existing_dirs:
        suggestions.append("有脚本文件散落在根目录，建议创建 scripts/ 目录整理")

    # 检查是否有测试图片散落
    has_test_images = any(
        "test" in f["name"].lower() and Path(f["name"]).suffix.lower() in {".png", ".jpg", ".jpeg"}
        for f in root_files
    )
    if has_test_images:
        suggestions.append("有测试图片散落在根目录，建议移动到 tests/ 目录")

    return {
        "project_type": proj_type,
        "missing_recommended": missing_recommended,
        "missing_optional": missing_optional,
        "suggestions": suggestions,
    }


def detect_directory_type(path: Path, items: List[Dict]) -> Dict[str, Any]:
    """
    检测目录类型和项目信息。

    Returns:
        {
            "type": "home" | "project" | "workspace" | "generic",
            "project_types": ["nodejs", "python", ...],
            "has_git": bool,
            "subprojects": [...],  # 工作区模式
        }
    """
    result = {
        "type": "generic",
        "project_types": [],
        "has_git": False,
        "subprojects": [],
    }

    item_names = {item["name"] for item in items}

    # 检查是否是主目录
    home_matches = item_names & HOME_MARKERS
    if len(home_matches) >= 3 or path == Path.home():
        result["type"] = "home"
        return result

    # 检查项目标识
    project_types = set()
    for item in items:
        name = item["name"]
        if name in PROJECT_MARKERS:
            project_types.add(PROJECT_MARKERS[name])
        if name == ".git":
            result["has_git"] = True

    if project_types:
        result["project_types"] = list(project_types)
        result["type"] = "project"
        return result

    # 检查是否是工作区（包含多个子项目）
    subprojects = []
    for item in items:
        if item["type"] == "dir":
            item_path = path / item["name"]
            # 检查子目录是否是项目
            try:
                sub_items = list(item_path.iterdir())
                sub_names = {p.name for p in sub_items}
                for marker, proj_type in PROJECT_MARKERS.items():
                    if marker in sub_names:
                        subprojects.append({
                            "name": item["name"],
                            "type": proj_type,
                            "size_kb": item.get("size_kb"),
                            "mtime": item.get("mtime"),
                        })
                        break
            except (PermissionError, OSError):
                pass

    if len(subprojects) >= 2:
        result["type"] = "workspace"
        result["subprojects"] = subprojects

    return result


def match_pattern(name: str, pattern: str) -> bool:
    """简单的通配符匹配，支持 * 在开头、中间或结尾"""
    pattern_lower = pattern.lower()
    name_lower = name.lower()

    if "*" not in pattern:
        return name_lower == pattern_lower

    if pattern.startswith("*") and pattern.endswith("*"):
        # *xxx* - 包含
        return pattern_lower[1:-1] in name_lower
    elif pattern.startswith("*"):
        # *xxx - 结尾匹配
        return name_lower.endswith(pattern_lower[1:])
    elif pattern.endswith("*"):
        # xxx* - 开头匹配
        return name_lower.startswith(pattern_lower[:-1])
    elif "*" in pattern:
        # xxx*yyy - 中间通配
        parts = pattern_lower.split("*", 1)
        return name_lower.startswith(parts[0]) and name_lower.endswith(parts[1])

    return False


def classify_item(name: str, path: Path, is_dir: bool) -> Dict[str, Any]:
    """
    对文件/目录进行分类。

    Returns:
        {
            "tag": str,
            "category": "cleanable" | "caution" | "protected" | "other",
            "description": str,
            "risk": "low" | "medium" | "high",
            "rebuild": bool,
        }
    """
    lowered = name.lower()

    # 检查可清理项
    for category, patterns in CLEANABLE_PATTERNS.items():
        # 精确目录匹配
        if is_dir and "dirs" in patterns:
            if lowered in patterns["dirs"] or name in patterns["dirs"]:
                return {
                    "tag": category,
                    "category": "cleanable",
                    "description": patterns["description"],
                    "risk": patterns.get("risk", "low"),
                    "rebuild": patterns.get("rebuild", False),
                }

        # 目录通配符匹配 (如 *.egg-info)
        if is_dir and "dir_patterns" in patterns:
            for pattern in patterns["dir_patterns"]:
                if match_pattern(name, pattern):
                    return {
                        "tag": category,
                        "category": "cleanable",
                        "description": patterns["description"],
                        "risk": patterns.get("risk", "low"),
                        "rebuild": patterns.get("rebuild", False),
                    }

        # 精确文件匹配
        if not is_dir and "files" in patterns:
            if name in patterns["files"] or lowered in patterns["files"]:
                return {
                    "tag": category,
                    "category": "cleanable",
                    "description": patterns["description"],
                    "risk": patterns.get("risk", "low"),
                    "rebuild": patterns.get("rebuild", False),
                }
            for pattern in patterns["files"]:
                if pattern.startswith("*"):
                    if name.endswith(pattern[1:]):
                        return {
                            "tag": category,
                            "category": "cleanable",
                            "description": patterns["description"],
                            "risk": patterns.get("risk", "low"),
                            "rebuild": patterns.get("rebuild", False),
                        }

        # 文件通配符匹配 (如 "* 2.*" 重复文件)
        if not is_dir and "file_patterns" in patterns:
            for pattern in patterns["file_patterns"]:
                if match_pattern(name, pattern):
                    return {
                        "tag": category,
                        "category": "cleanable",
                        "description": patterns["description"],
                        "risk": patterns.get("risk", "low"),
                        "rebuild": patterns.get("rebuild", False),
                    }

    # 检查需谨慎处理项
    for category, patterns in CAUTION_PATTERNS.items():
        if is_dir and "dirs" in patterns:
            for pattern in patterns["dirs"]:
                if pattern.startswith("*"):
                    if lowered.endswith(pattern[1:]) or lowered.startswith(pattern[1:]):
                        return {
                            "tag": category,
                            "category": "caution",
                            "description": patterns["description"],
                            "risk": "medium",
                            "rebuild": False,
                        }
                elif lowered == pattern.lower():
                    return {
                        "tag": category,
                        "category": "caution",
                        "description": patterns["description"],
                        "risk": "medium",
                        "rebuild": False,
                    }
        if not is_dir and "files" in patterns:
            for pattern in patterns["files"]:
                if pattern.startswith("*"):
                    if name.endswith(pattern[1:]):
                        return {
                            "tag": category,
                            "category": "caution",
                            "description": patterns["description"],
                            "risk": "medium",
                            "rebuild": False,
                        }
                elif name == pattern:
                    return {
                        "tag": category,
                        "category": "caution",
                        "description": patterns["description"],
                        "risk": "medium",
                        "rebuild": False,
                    }

    # 检查受保护项
    for category, patterns in PROTECTED_PATTERNS.items():
        if is_dir and "dirs" in patterns:
            if lowered in patterns["dirs"] or name in patterns["dirs"]:
                return {
                    "tag": category,
                    "category": "protected",
                    "description": f"受保护: {category}",
                    "risk": "high",
                    "rebuild": False,
                }

    # Dotfiles
    if name.startswith("."):
        return {
            "tag": "dotfile",
            "category": "other",
            "description": "配置文件",
            "risk": "medium",
            "rebuild": False,
        }

    return {
        "tag": "other",
        "category": "other",
        "description": "",
        "risk": "low",
        "rebuild": False,
    }


# ============ 扫描逻辑 ============

def get_mtime(path: Path) -> Optional[str]:
    """获取修改时间（ISO 格式）"""
    try:
        mtime = path.stat().st_mtime
        return datetime.fromtimestamp(mtime).isoformat()
    except Exception:
        return None


def count_children(path: Path) -> Optional[int]:
    """计算直接子项数量"""
    if not path.is_dir():
        return None
    try:
        return sum(1 for _ in path.iterdir())
    except PermissionError:
        return None


def scan_directory(
    target: Path,
    depth: int = 1,
    current_depth: int = 0,
    include_hidden: bool = True,
    parent_path: str = ""
) -> List[Dict[str, Any]]:
    """
    扫描目录。

    Args:
        target: 要扫描的目录
        depth: 扫描深度（1=只看顶层）
        current_depth: 当前深度
        include_hidden: 是否包含隐藏文件
        parent_path: 父路径（用于相对路径显示）

    Returns:
        项目信息列表
    """
    items = []

    try:
        entries = sorted(target.iterdir(), key=lambda p: p.name.lower())
    except PermissionError:
        return items

    for entry in entries:
        name = entry.name

        # 跳过隐藏项（如果设置）
        if not include_hidden and name.startswith("."):
            continue

        try:
            stat = entry.lstat()
        except (OSError, IOError) as e:
            items.append({
                "name": name,
                "path": str(entry) if current_depth > 0 else name,
                "relative_path": f"{parent_path}/{name}" if parent_path else name,
                "type": "error",
                "depth": current_depth,
                "error": str(e),
            })
            continue

        # 确定类型
        is_symlink = entry.is_symlink()
        is_dir = entry.is_dir() and not is_symlink

        if is_symlink:
            entry_type = "symlink"
        elif is_dir:
            entry_type = "dir"
        else:
            entry_type = "file"

        # 获取大小
        size_kb = get_size(entry)
        if size_kb is None:
            size_kb = stat.st_size // 1024

        # 分类
        classification = classify_item(name, entry, is_dir)

        relative_path = f"{parent_path}/{name}" if parent_path else name

        item = {
            "name": name,
            "path": str(entry) if current_depth > 0 else name,
            "relative_path": relative_path,
            "type": entry_type,
            "depth": current_depth,
            "size_kb": size_kb,
            "children": count_children(entry) if is_dir else None,
            "mtime": get_mtime(entry),
            **classification,
        }

        items.append(item)

        # 递归扫描（如果需要）
        if is_dir and current_depth < depth - 1:
            # 跳过某些不需要深入的目录
            skip_dirs = {"node_modules", ".git", ".venv", "venv", "__pycache__", ".idea"}
            if name not in skip_dirs:
                sub_items = scan_directory(
                    entry,
                    depth=depth,
                    current_depth=current_depth + 1,
                    include_hidden=include_hidden,
                    parent_path=relative_path
                )
                items.extend(sub_items)

    return items


def detect_warnings(target: Path) -> List[str]:
    """检测潜在问题并生成警告"""
    warnings = []

    if not os.access(target, os.W_OK):
        warnings.append("目标不可写（可能只读挂载）")

    # 云盘检测
    cloud_markers = {
        "Mobile Documents": "iCloud",
        "OneDrive": "OneDrive",
        "Dropbox": "Dropbox",
        "Google Drive": "Google Drive",
    }
    target_str = str(target)
    for marker, service in cloud_markers.items():
        if marker in target_str:
            warnings.append(f"检测到 {service} 云盘路径（Git 备份已提供保护，可安全操作）")
            break

    return warnings


# ============ 输出格式化 ============

def format_size(kb: Optional[int]) -> str:
    """格式化大小显示"""
    if kb is None:
        return "N/A"
    if kb < 1024:
        return f"{kb}K"
    mb = kb / 1024
    if mb < 1024:
        return f"{mb:.1f}M"
    gb = mb / 1024
    return f"{gb:.1f}G"


def print_table(items: List[Dict], sort_key: str = "size") -> None:
    """打印表格格式输出"""
    if not items:
        print("(empty)")
        return

    # 过滤顶层项目用于显示
    top_items = [i for i in items if i["depth"] == 0]

    name_width = max((len(item["relative_path"]) for item in top_items), default=4)
    name_width = min(name_width, 40)

    header = f"{'NAME'.ljust(name_width)}  {'TYPE':<8} {'SIZE':>8}  {'CATEGORY':<12} {'TAG':<15}"
    print(header)
    print("-" * len(header))

    def sort_fn(item: Dict) -> tuple:
        if sort_key == "size":
            return (-(item["size_kb"] or 0), item["name"].lower())
        elif sort_key == "category":
            return (item.get("category", ""), item["name"].lower())
        else:
            return (item["name"].lower(),)

    for item in sorted(top_items, key=sort_fn):
        name = item["relative_path"][:name_width]
        entry_type = item["type"]
        size = format_size(item["size_kb"])
        category = item.get("category", "-")
        tag = item.get("tag", "-")

        print(f"{name.ljust(name_width)}  {entry_type:<8} {size:>8}  {category:<12} {tag:<15}")


def generate_summary(items: List[Dict], dir_info: Dict, misplaced: List[Dict], duplicates: List[Dict], structure: Dict) -> Dict:
    """生成摘要统计"""
    summary = {
        "total_items": len([i for i in items if i["depth"] == 0]),
        "total_size_kb": sum(i.get("size_kb", 0) or 0 for i in items if i["depth"] == 0),
        "by_category": {},
        "by_tag": {},
        "cleanable_size_kb": 0,
        "caution_size_kb": 0,
        # 新增：整理相关
        "misplaced_count": len(misplaced),
        "misplaced_size_kb": sum(m.get("size_kb", 0) or 0 for m in misplaced),
        "duplicate_count": len(duplicates),
        "duplicate_size_kb": sum(d.get("size_kb", 0) or 0 for d in duplicates),
        "structure_suggestions": len(structure.get("suggestions", [])),
    }

    for item in items:
        if item["depth"] != 0:
            continue

        category = item.get("category", "other")
        tag = item.get("tag", "other")
        size = item.get("size_kb", 0) or 0

        summary["by_category"][category] = summary["by_category"].get(category, 0) + 1
        summary["by_tag"][tag] = summary["by_tag"].get(tag, 0) + 1

        if category == "cleanable":
            summary["cleanable_size_kb"] += size
        elif category == "caution":
            summary["caution_size_kb"] += size

    return summary


def print_json(target: Path, items: List[Dict], warnings: List[str], dir_info: Dict,
               misplaced: List[Dict], duplicates: List[Dict], structure: Dict) -> None:
    """打印 JSON 格式输出"""
    summary = generate_summary(items, dir_info, misplaced, duplicates, structure)

    output = {
        "target": str(target),
        "scanned_at": datetime.now().isoformat(),
        "platform": platform.system(),
        "directory_info": dir_info,
        "warnings": warnings,
        "summary": summary,
        # 核心整理信息
        "misplaced_files": misplaced,
        "duplicate_files": duplicates,
        "structure_suggestions": structure,
        # 详细项目列表
        "items": items,
    }

    print(json.dumps(output, indent=2, ensure_ascii=False))


def print_organization_report(misplaced: List[Dict], duplicates: List[Dict], structure: Dict) -> None:
    """打印整理报告（人类可读格式）"""

    # 1. 结构建议
    if structure.get("suggestions"):
        print("\n📁 结构建议")
        print("-" * 40)
        for s in structure["suggestions"]:
            print(f"  • {s}")

    # 2. 散落文件
    if misplaced:
        print("\n📄 散落文件（建议移动）")
        print("-" * 40)

        # 按建议目录分组
        by_dir = {}
        for m in misplaced:
            suggested = m["suggested_dir"]
            if suggested not in by_dir:
                by_dir[suggested] = []
            by_dir[suggested].append(m)

        for suggested_dir, files in by_dir.items():
            dir_marker = "✓" if files[0]["dir_exists"] else "+"
            print(f"\n  → {suggested_dir}/ [{dir_marker}]")
            for f in files:
                size = format_size(f["size_kb"])
                print(f"      {f['file']:<35} {size:>8}")

    # 3. 重复文件
    if duplicates:
        print("\n🔄 重复文件（建议删除）")
        print("-" * 40)

        # 按位置分组
        by_loc = {}
        for d in duplicates:
            loc = d["location"]
            if loc not in by_loc:
                by_loc[loc] = []
            by_loc[loc].append(d)

        for loc, files in by_loc.items():
            print(f"\n  📂 {loc}")
            for f in files:
                original_mark = "✓" if f["original_exists"] else "?"
                size = format_size(f["size_kb"])
                print(f"      {f['duplicate']:<30} → {f['original']} [{original_mark}] {size:>8}")

    # 总结
    total_misplaced = len(misplaced)
    total_duplicates = len(duplicates)

    if total_misplaced > 0 or total_duplicates > 0:
        print("\n" + "=" * 40)
        print("整理建议汇总:")
        if total_misplaced > 0:
            print(f"  • {total_misplaced} 个文件建议移动到正确目录")
        if total_duplicates > 0:
            print(f"  • {total_duplicates} 个重复文件建议删除")
    elif not structure.get("suggestions"):
        print("\n✨ 项目结构良好，无需整理")


# ============ 主入口 ============

def main() -> int:
    parser = argparse.ArgumentParser(
        description="目录清点工具 - 支持主目录和项目目录整理",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s --target ~                     # 扫描主目录（顶层）
  %(prog)s --target . --depth 2           # 扫描当前目录，深度2层
  %(prog)s --target ~/workspace --depth 2 # 扫描工作区
  %(prog)s --target . --json              # JSON 输出
  %(prog)s --target . --sort category     # 按分类排序
        """
    )

    parser.add_argument(
        "--target", "-t",
        default=".",
        help="要扫描的目录（默认: 当前目录）"
    )
    parser.add_argument(
        "--depth", "-d",
        type=int,
        default=1,
        help="扫描深度（默认: 1，只看顶层）"
    )
    parser.add_argument(
        "--sort", "-s",
        choices=["name", "size", "category"],
        default="size",
        help="排序方式（默认: size）"
    )
    parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="输出 JSON 格式"
    )
    parser.add_argument(
        "--no-hidden",
        action="store_true",
        help="不包含隐藏文件/目录"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="显示详细文件列表"
    )

    args = parser.parse_args()

    target = Path(args.target).expanduser().resolve()

    if not target.exists():
        print(f"Error: Path does not exist: {target}", file=sys.stderr)
        return 1

    if not target.is_dir():
        print(f"Error: Path is not a directory: {target}", file=sys.stderr)
        return 1

    # 扫描
    items = scan_directory(
        target,
        depth=args.depth,
        include_hidden=not args.no_hidden
    )

    # 检测目录类型
    top_items = [i for i in items if i["depth"] == 0]
    dir_info = detect_directory_type(target, top_items)

    # 检测警告
    warnings = detect_warnings(target)

    # 整理分析
    project_types = dir_info.get("project_types", [])
    misplaced = detect_misplaced_files(items, project_types)
    duplicates = detect_duplicate_files(items)
    structure = suggest_structure(items, project_types)

    # 输出
    if args.json:
        print_json(target, items, warnings, dir_info, misplaced, duplicates, structure)
    else:
        print(f"Inventory for: {target}")
        print(f"Directory type: {dir_info['type']}")
        if dir_info.get("project_types"):
            print(f"Project types: {', '.join(dir_info['project_types'])}")
        if dir_info.get("subprojects"):
            print(f"Subprojects: {len(dir_info['subprojects'])}")
        print()

        if warnings:
            for w in warnings:
                print(f"⚠️  {w}")
            print()

        # 核心：整理报告
        print_organization_report(misplaced, duplicates, structure)

        # 详细文件列表（可选）
        if args.verbose:
            print("\n" + "=" * 40)
            print("详细文件列表:")
            print_table(items, sort_key=args.sort)

        # 摘要
        summary = generate_summary(items, dir_info, misplaced, duplicates, structure)
        total_size = summary["total_size_kb"]

        print()
        print(f"Total: {summary['total_items']} items, {format_size(total_size)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
