---
name: project-organizer
description: 智能项目整理工具。分析项目性质，规划合理目录结构，整理散落文件，清理重复文件。让项目结构清晰规范。
trigger:
  - "整理这个项目"
  - "整理项目"
  - "项目太乱了"
  - "帮我整理"
  - "规范项目结构"
  - "organize project"
  - "clean up project"
  - "tidy up"
tools:
  - Bash
  - Read
  - Write
  - Glob
---

# Project Organizer

**智能项目整理工具** - 理解项目，规划结构，整理文件。

核心流程：
1. **读项目** - 看代码结构、入口文件、配置，了解项目真实情况（文档可能过时）
2. **规划结构** - 根据项目类型确定合理的目录结构
3. **识别问题** - 找出散落文件、重复文件、结构问题
4. **执行整理** - 在 Git 备份保护下执行整理操作

**不关注**：依赖目录（.venv、node_modules）和构建产物（除非用户要求清理空间）

## 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                 Claude 智能分析层                            │
│                                                              │
│  1. 读项目代码（目录结构、入口文件、配置）了解真实情况       │
│  2. 识别项目类型（库、应用、CLI、数据项目等）                │
│  3. 确定合理的目录结构方案                                   │
│  4. 与用户确认结构方案                                       │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                 问题识别层                                   │
│                                                              │
│  1. 运行清点脚本，扫描当前结构                               │
│  2. 对比目标结构，识别需要整理的内容                         │
│  3. 识别散落文件、重复文件                                   │
│  4. 生成整理计划                                             │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                 安全执行层                                   │
│                                                              │
│  - Git 备份保护（必须）                                      │
│  - 用户确认后执行                                            │
│  - 支持随时恢复                                              │
└─────────────────────────────────────────────────────────────┘
```

## 目录类型识别

Claude 首先识别目标目录的类型：

| 类型 | 特征 | 分析策略 |
|------|------|----------|
| **主目录** | 路径为 `~` 或包含 Desktop/Documents/Downloads | 顶层分类，关注结构组织 |
| **项目目录** | 包含 `.git`、`package.json`、`pyproject.toml` 等 | 关注构建产物、依赖、临时文件 |
| **工作区** | 包含多个子项目 | 混合策略，识别活跃/归档项目 |
| **普通目录** | 其他 | 通用文件分类 |

## Claude 执行指令

### Phase 0: Git 备份（必须）

**在任何整理操作前，必须先创建 Git 备份：**

```bash
python3 ~/.claude/skills/project-organizer/scripts/git_backup.py before -m "整理前备份"
```

### Phase 1: 理解项目（关键步骤）

**读项目，而非只读文档**（文档可能过时，代码才是真相）：

```bash
# 1. 先看目录结构，了解项目骨架
ls -la
ls */  # 看主要子目录

# 2. 看配置文件，了解项目类型和依赖
cat pyproject.toml 或 package.json 或 Cargo.toml

# 3. 看核心代码入口
cat <main_module>/__init__.py  # Python
cat src/index.ts               # Node.js
cat main.go                    # Go

# 4. 看测试结构，了解项目组织方式
ls tests/

# 5. 最后看文档（仅作参考）
cat README.md
```

**通过代码理解项目：**

| 看什么 | 了解什么 |
|--------|----------|
| 目录结构 | 项目的实际组织方式 |
| `__init__.py` / 入口文件 | 核心模块和功能 |
| 配置文件 | 项目类型、依赖、构建方式 |
| 测试目录 | 项目的测试策略和覆盖范围 |
| imports 语句 | 模块间的依赖关系 |

**需要确认的问题：**
1. 这是什么类型的项目？（库、应用、CLI工具、数据项目等）
2. 项目的核心模块/功能是什么？
3. 当前的目录结构是有意设计的，还是随意放置的？
4. 哪些目录是核心的，哪些是临时/实验性的？

### Phase 2: 确定目标结构

**根据项目类型确定合理的目录结构：**

| 项目类型 | 推荐结构 |
|----------|----------|
| **Python 库** | `src/<pkg>/`, `tests/`, `docs/`, `examples/` |
| **Python 应用** | `<app>/`, `tests/`, `scripts/`, `config/` |
| **CLI 工具** | `src/`, `tests/`, `docs/` |
| **数据/ML 项目** | `src/`, `notebooks/`, `data/`, `models/`, `output/` |
| **文档项目** | `docs/`, `assets/`, `examples/` |

**向用户确认：**
```
根据 README，这是一个 [项目类型] 项目。

建议的目录结构：
├── ocrmac/          # 核心代码（保持不变）
├── tests/           # 测试（已存在）
├── docs/            # 文档（已存在）
├── examples/        # 示例代码（已存在）
├── notebooks/       # Jupyter notebooks（建议创建）
├── scripts/         # 工具脚本（建议创建）
└── output/          # 输出文件（已存在）

这个结构是否符合你的预期？需要调整吗？
```

### Phase 3: 扫描并识别问题

```bash
# 方式1：从项目目录运行（推荐）
python3 ~/.claude/skills/project-organizer/scripts/root_inventory.py --depth 3

# 方式2：指定目标目录
python3 ~/.claude/skills/project-organizer/scripts/root_inventory.py --target /path/to/project --depth 3
```

脚本会输出：
1. **结构建议** - 缺失的标准目录
2. **散落文件** - 放错位置的文件及建议目录
3. **重复文件** - macOS 复制产生的重复文件

### Phase 4: 智能分析

Claude 结合**项目理解**和**脚本输出**进行智能判断：

#### 散落文件处理

对于每个散落文件，Claude 需要判断：

1. **是否真的需要移动？**
   - notebooks 散落在根目录 → 建议移动到 `notebooks/`
   - 测试图片在根目录 → 建议移动到 `tests/images/`
   - 但如果是 README 引用的图片 → 保留在根目录

2. **是否符合目标结构？**
   - 参照 Phase 2 确定的目标结构
   - 确保移动后的位置合理

3. **批量 vs 逐个确认**
   - 同类文件（如所有 notebooks）可以批量确认
   - 不确定的文件单独询问

#### 重复文件处理

1. **确认是否真的重复**
   ```bash
   diff "original.py" "original 2.py"
   ```
   - 完全相同 → 直接删除副本
   - 有差异 → 询问保留哪个

2. **`[✓]` 标记含义**
   - 表示原文件存在，副本可安全删除
   - `[?]` 表示原文件不存在，需要谨慎处理

### Phase 5: 向用户展示整理计划

**示例输出：**

```
## 项目整理计划: ~/workspace/my-app

### 📁 需要创建的目录
- notebooks/  (存放 Jupyter notebooks)
- scripts/    (存放脚本文件)

### 📄 散落文件归位
| 文件 | 移动到 | 说明 |
|------|--------|------|
| BlogTest.ipynb | notebooks/ | Jupyter notebook |
| ExampleNotebook.ipynb | notebooks/ | Jupyter notebook |
| test.png | tests/images/ | 测试图片 |
| run_ocrmac.sh | scripts/ | 脚本文件 |

### 🔄 重复文件清理
| 重复文件 | 原文件 | 状态 |
|----------|--------|------|
| debug_test 2.py | debug_test.py | ✓ 相同，可删除 |
| layout_analyzer 2.py | layout_analyzer.py | ✓ 相同，可删除 |

### 执行计划
1. 创建 2 个新目录
2. 移动 4 个散落文件
3. 删除 2 个重复文件

确认执行？[y/N]
```

### Phase 6: 执行整理

用户确认后，Claude 直接执行：

```bash
# 1. 创建目录
mkdir -p notebooks scripts tests/images

# 2. 移动散落文件
mv BlogTest.ipynb ExampleNotebook.ipynb RegenerateTestImages.ipynb notebooks/
mv run_ocrmac.sh scripts/
mv test.png wikipedia_test.png tests/images/

# 3. 删除重复文件（确认后）
rm "tests/debug_test 2.py"
rm "tests/debug_heading 2.py"
rm "ocrmac/layout_analyzer 2.py"
# ... 等等
```

### Phase 7: 完成并验证

```bash
# 查看整理后的更改
python3 ~/.claude/skills/project-organizer/scripts/git_backup.py after

# 输出会显示所有更改，让用户检查
```

用户检查后：

```bash
# 如果满意，确认整理结果
python3 ~/.claude/skills/project-organizer/scripts/git_backup.py confirm

# 如果不满意，恢复到整理前
python3 ~/.claude/skills/project-organizer/scripts/git_backup.py restore
```

**注意**：
- 移动操作简单安全，直接执行
- 删除操作需要用户确认
- Git 备份确保任何操作都可恢复

## 散落文件识别规则

### 常见散落文件类型

| 文件类型 | 特征 | 建议目录 |
|----------|------|----------|
| Jupyter Notebooks | `*.ipynb` | `notebooks/` |
| 脚本文件 | `*.sh` (非标准脚本) | `scripts/` |
| 测试图片 | `test*.png`, `*_test.jpg` | `tests/images/` |
| 输出图片 | `output*.png`, `result*.jpg` | `output/` |
| Skill 文件 | `*.skill` | `skills/` |

### 重复文件模式

| 模式 | 示例 | 来源 |
|------|------|------|
| `* 2.*` | `file 2.py` | macOS Finder 复制 |
| `* 3.*` | `file 3.py` | 多次复制 |
| `*副本*` | `文件副本.txt` | 中文系统复制 |
| `*copy*` | `file copy.py` | 手动复制 |

### 标准项目目录结构

**Python 项目**：
```
project/
├── src/ 或 <package_name>/  # 源代码
├── tests/                   # 测试
├── docs/                    # 文档
├── scripts/                 # 脚本工具
├── notebooks/               # Jupyter notebooks
├── examples/                # 示例代码
└── output/                  # 输出文件
```

### 不应移动的文件

| 文件 | 原因 |
|------|------|
| `README.md` | 项目文档，应在根目录 |
| `setup.py`, `pyproject.toml` | 项目配置 |
| `requirements.txt` | 依赖声明 |
| `.gitignore` | Git 配置 |
| `Makefile` | 构建配置 |
| `LICENSE` | 许可证 |

## 工作区整理

对于包含多个项目的工作区，整理思路：

```bash
# 扫描工作区
python3 ~/.claude/skills/project-organizer/scripts/root_inventory.py --target ~/workspace --depth 2
```

分析要点：
1. 每个子项目的结构是否规范
2. 是否有跨项目的重复文件
3. 不活跃项目是否应该归档

**不关注依赖和构建产物**，除非用户明确要求清理空间。

## 安全规则

### 三层安全保障

```
┌─────────────────────────────────────────────────────────────┐
│  第一层：Git 备份                                            │
│  - 整理前自动创建备份分支                                    │
│  - 可随时恢复到整理前状态                                    │
│  - 命令: git_backup.py before/restore                       │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  第二层：受保护路径                                          │
│  - 系统路径、用户配置路径自动跳过                            │
│  - .git、src、tests 等核心目录不动                          │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  第三层：用户确认                                            │
│  - 所有删除操作需要用户确认                                  │
│  - 不确定的移动操作单独询问                                  │
└─────────────────────────────────────────────────────────────┘
```

### Git 备份工作流

| 阶段 | 命令 | 说明 |
|------|------|------|
| 整理前 | `git_backup.py before` | **必须** - 创建备份分支 |
| 整理后 | `git_backup.py after` | 显示更改，等待用户检查 |
| 满意 | `git_backup.py confirm` | 清理备份分支 |
| 不满意 | `git_backup.py restore` | 恢复到整理前状态 |

### 移动操作安全性

| 操作类型 | 风险 | 处理方式 |
|----------|------|----------|
| 移动到已存在目录 | 低 | 直接 mv |
| 移动到新目录 | 低 | 先 mkdir -p，再 mv |
| 批量移动多个文件 | 中 | Git 备份已覆盖 |

### 删除操作安全性

| 操作类型 | 风险 | 处理方式 |
|----------|------|----------|
| 删除重复文件（原文件存在） | 低 | 确认后直接 rm |
| 删除重复文件（原文件不存在） | 高 | 询问用户 |
| 删除系统文件 (.DS_Store) | 低 | 可直接删除 |

### 绝对不动的路径

- `.git/` - 版本控制
- `src/`, `lib/`, `app/` - 源代码目录
- `tests/` - 测试代码（内部整理除外）
- 配置文件（`package.json`, `pyproject.toml`, `.env` 等）

## Claude 智能判断指南

Claude 运用模型能力进行智能判断，不只依赖脚本分类。

### 散落文件判断

脚本会标记"散落文件"，但 Claude 需要判断：

1. **是否真的应该移动？**
   - `test.png` 在根目录 → 如果 README 引用了它，就不应移动
   - `example.ipynb` 在根目录 → 如果是项目主要示例，可能应保留

2. **检查引用关系**
   ```bash
   # 检查 README 是否引用了这个图片
   grep -l "test.png" README.md
   ```

3. **询问不确定的情况**
   ```
   发现 test.png 在根目录，但 README.md 中引用了它。
   建议保留在原位置，还是移动到 tests/images/ 并更新引用？
   ```

### 重复文件判断

1. **确认是否真的重复**
   ```bash
   diff "original.py" "original 2.py"
   ```
   - 完全相同 → 直接删除副本
   - 有差异 → 询问保留哪个

2. **批量展示，统一确认**
   ```
   发现 12 个重复文件，全部与原文件相同。
   确认删除？[y/N]
   ```

### 上下文感知

| 用户说... | Claude 关注... |
|-----------|----------------|
| "项目太乱了" | 散落文件、重复文件、目录结构 |
| "整理一下" | 同上 |
| "清理空间" | 依赖缓存、构建产物（不同于默认行为） |
| "删除重复文件" | 只处理重复文件 |

**默认行为**：整理结构，不删除依赖/构建产物。

## 示例对话

### 示例 1: 完整整理流程（含项目理解）

```
User: 这个项目太乱了，帮我整理一下

Claude: 好的，让我先了解这个项目，再制定整理方案。

## Phase 0: 创建备份
[运行 git_backup.py before]
✓ 备份分支已创建

## Phase 1: 理解项目
[查看目录结构和核心代码]

```
ls -la → 看到 ocrmac/, tests/, docs/, examples/
cat pyproject.toml → Python 库，依赖 pyobjc
cat ocrmac/__init__.py → 核心是 OCR 类，提供 recognize() 方法
```

这是 **ocrmac** - 一个 Python OCR 库：
- 使用 macOS Vision 框架
- 核心模块：ocrmac/ocr.py, ocrmac/cli.py
- 有完整的测试和文档

## Phase 2: 确定目标结构

根据项目性质（Python 库 + CLI），建议结构：
```
ocrmac/
├── ocrmac/          # 核心代码 ✓
├── tests/           # 测试 ✓
├── docs/            # 文档 ✓
├── examples/        # 示例 ✓
├── notebooks/       # Jupyter demos ← 建议创建
├── scripts/         # 工具脚本 ← 建议创建
└── output/          # 输出 ✓
```

这个结构符合你的预期吗？

User: 可以

Claude: 好的，现在扫描具体问题...

## Phase 3-4: 扫描并分析
[运行 root_inventory.py --depth 3]

## 📄 散落文件 (8 个)
| 文件 | 移动到 |
|------|--------|
| BlogTest.ipynb, ExampleNotebook.ipynb | notebooks/ |
| test.png, wikipedia_test.png | tests/images/ |
| run_ocrmac.sh | scripts/ |

## 🔄 重复文件 (12 个)
所有重复文件都与原文件相同，可删除。

## Phase 5: 整理计划
1. 创建 notebooks/, scripts/ 目录
2. 移动 8 个散落文件
3. 删除 12 个重复文件

确认执行？

User: 执行

Claude: 开始整理...

mkdir -p notebooks scripts tests/images
mv BlogTest.ipynb ExampleNotebook.ipynb notebooks/
mv run_ocrmac.sh scripts/
mv test.png wikipedia_test.png tests/images/
rm "tests/debug_test 2.py" ...

✓ 整理完成

[运行 git_backup.py after]
如满意: git_backup.py confirm
如需恢复: git_backup.py restore

User: 确认

Claude:
[运行 git_backup.py confirm]
✓ 项目整理完成！
```

### 示例 2: 只整理部分

```
User: 项目有点乱，但我只想清理重复文件，其他不动

Claude: 好的，让我先创建备份，然后只检查重复文件...

[运行 git_backup.py before]
✓ 备份已创建

[运行 root_inventory.py --depth 3]

发现 12 个重复文件：

| 位置 | 重复文件 | 原文件 |
|------|----------|--------|
| tests/ | debug_test 2.py | debug_test.py ✓ |
| tests/ | debug_heading 2.py | debug_heading.py ✓ |
| ocrmac/ | layout_analyzer 2.py | layout_analyzer.py ✓ |
...

所有重复文件都与原文件相同，可以安全删除。
确认删除这 12 个重复文件？

User: 确认

Claude: 删除中...

rm "tests/debug_test 2.py"
rm "tests/debug_heading 2.py"
...

✓ 12 个重复文件已删除

[运行 git_backup.py after]
已删除 12 个文件。

如果满意，运行: git_backup.py confirm
如需恢复，运行: git_backup.py restore
```

### 示例 3: 恢复操作

```
User: 刚才整理错了，帮我恢复

Claude: 好的，让我检查备份状态...

[运行 git_backup.py status]
当前有活跃的整理会话：
  backup_branch=backup/dir-organizer-20240119_160000

确认恢复到整理前的状态？

User: 确认

Claude:
[运行 git_backup.py restore -y]
✓ 已恢复到备份状态

所有整理操作已撤销，项目恢复到整理前的状态。
```

## 文件说明

| 文件 | 用途 |
|------|------|
| `scripts/root_inventory.py` | **核心**：目录扫描 + 整理分析 |
| `scripts/git_backup.py` | **核心**：Git 备份/恢复工具 |
| `scripts/safe_executor.py` | 可选：批量移动时的安全执行 |
| `scripts/transaction_log.py` | 可选：事务日志模块 |
| `references/protected-paths.md` | 参考：受保护路径 |
| `references/classification-heuristics.md` | 参考：分类规则 |
| `references/validation-checklist.md` | 参考：验证清单 |
| `references/project-cleanup-rules.md` | 参考：项目清理规则（仅当用户要求清理空间时使用） |
