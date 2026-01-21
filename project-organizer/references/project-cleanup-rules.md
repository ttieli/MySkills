# 项目清理规则

针对不同类型项目的清理指南。

## 通用规则

### 安全删除（低风险）

这些可以直接删除，不需要事务日志：

| 类型 | 路径 | 重建方式 |
|------|------|----------|
| Python 字节码 | `__pycache__/`, `*.pyc` | 自动重建 |
| pytest 缓存 | `.pytest_cache/` | 自动重建 |
| mypy 缓存 | `.mypy_cache/` | 自动重建 |
| ruff 缓存 | `.ruff_cache/` | 自动重建 |
| 覆盖率报告 | `coverage/`, `htmlcov/`, `.coverage` | `pytest --cov` |
| tox 环境 | `.tox/` | `tox` |
| 构建输出 | `dist/`, `build/`, `out/` | 构建命令 |

### 可重建但较大（中等风险）

需要网络下载或较长时间重建：

| 类型 | 路径 | 重建方式 | 注意事项 |
|------|------|----------|----------|
| Node 依赖 | `node_modules/` | `npm install` | 需要网络 |
| Python 虚拟环境 | `.venv/`, `venv/` | `python -m venv` + `pip install` | 检查是否有本地修改 |
| Go 模块缓存 | `vendor/` | `go mod vendor` | 需要网络 |
| Ruby 依赖 | `.bundle/`, `vendor/bundle/` | `bundle install` | 需要网络 |
| iOS 依赖 | `Pods/` | `pod install` | 需要网络 |

### 谨慎处理（高风险）

可能包含重要数据，需用户确认：

| 类型 | 路径 | 判断方法 |
|------|------|----------|
| 数据文件 | `data/`, `datasets/` | 检查大小和内容 |
| 模型文件 | `models/`, `*.h5`, `*.pt` | 询问用户，可能训练耗时 |
| 数据库 | `*.db`, `*.sqlite` | 可能是生产数据 |
| 环境变量 | `.env` | 可能包含密钥 |
| 备份 | `*backup*`, `*.bak` | 询问用户 |

### 绝对不动

| 类型 | 路径 | 原因 |
|------|------|------|
| 源代码 | `src/`, `lib/`, `app/` | 核心代码 |
| 测试 | `tests/`, `test/` | 测试代码 |
| 版本控制 | `.git/` | 历史记录 |
| 配置 | `package.json`, `pyproject.toml` | 项目配置 |
| 文档 | `docs/`, `README.md` | 文档 |

---

## 按项目类型

### Node.js / JavaScript

```bash
# 安全删除
rm -rf node_modules/
rm -rf dist/ build/ out/ .next/ .nuxt/
rm -rf coverage/ .nyc_output/
rm -rf .cache/ .parcel-cache/

# 重建
npm install  # 或 yarn / pnpm install
npm run build
```

**大小估算**：
- `node_modules/`: 通常 200MB - 2GB
- `.next/`: 50MB - 500MB

**注意**：
- 检查是否有 `node_modules` 中的本地修改（`npm link` 等）
- monorepo 中每个 package 都有 `node_modules`

### Python

```bash
# 安全删除
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
rm -rf .pytest_cache/ .mypy_cache/ .ruff_cache/
rm -rf .tox/ .coverage htmlcov/
rm -rf dist/ build/ *.egg-info/

# 虚拟环境（确认后删除）
rm -rf .venv/ venv/

# 重建
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt  # 或 pip install -e .
```

**大小估算**：
- `.venv/`: 通常 100MB - 1GB
- `__pycache__/`: 通常 1-50MB

**注意**：
- 检查 `.venv/` 中是否有 `pip install -e` 的本地包
- 某些项目使用 `conda`，环境可能更大

### Rust

```bash
# 安全删除
rm -rf target/

# 重建
cargo build
```

**大小估算**：
- `target/`: 通常 500MB - 5GB（Rust 编译产物很大）

### Go

```bash
# 安全删除
rm -rf vendor/  # 如果使用 go mod vendor

# 重建
go mod vendor
go build
```

### Java / Kotlin

```bash
# 安全删除
rm -rf target/          # Maven
rm -rf build/           # Gradle
rm -rf .gradle/

# 重建
mvn clean install       # Maven
./gradlew build         # Gradle
```

**大小估算**：
- `target/` / `build/`: 通常 100MB - 1GB

### Docker

```bash
# 项目级别
rm -rf .docker/

# 系统级别（谨慎）
docker system prune -a  # 删除所有未使用的镜像、容器、网络
docker volume prune     # 删除未使用的卷
```

---

## 工作区清理

对于包含多个项目的工作区：

### 批量清理依赖

```bash
# 查找所有 node_modules
find ~/workspace -name "node_modules" -type d -prune

# 计算总大小
find ~/workspace -name "node_modules" -type d -prune -exec du -sh {} \;

# 批量删除（谨慎）
find ~/workspace -name "node_modules" -type d -prune -exec rm -rf {} \;

# 同样适用于 .venv
find ~/workspace -name ".venv" -type d -prune -exec du -sh {} \;
```

### 识别不活跃项目

```bash
# 查找超过 180 天未修改的目录
find ~/workspace -maxdepth 1 -type d -mtime +180

# 按修改时间排序
ls -lt ~/workspace
```

### 清理策略建议

| 项目状态 | 建议操作 |
|----------|----------|
| 活跃开发 | 只清理构建产物 |
| 偶尔使用 | 清理依赖，保留源码 |
| 长期不用 | 归档到 `~/archive/` |
| 确认不需要 | 删除（先备份） |

---

## 大文件处理

### 识别大文件

```bash
# 查找大于 100MB 的文件
find . -type f -size +100M -exec ls -lh {} \;

# 按大小排序
du -ah . | sort -rh | head -20
```

### 常见大文件类型

| 类型 | 扩展名 | 处理建议 |
|------|--------|----------|
| ML 模型 | `.h5`, `.pt`, `.onnx`, `.pkl` | 询问用户，可能需要保留 |
| 数据集 | `.csv`, `.parquet`, `.json` (大) | 检查是否可从源重新下载 |
| 日志 | `.log` | 通常可以安全删除 |
| 压缩包 | `.zip`, `.tar.gz` | 检查是否已解压 |
| 二进制 | `.exe`, `.dll`, `.so` | 检查是否是构建产物 |
| 视频/音频 | `.mp4`, `.mp3` | 可能是测试资源 |

---

## 清理命令速查

```bash
# === Python ===
# 删除所有 __pycache__
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# 删除所有 .pyc
find . -type f -name "*.pyc" -delete

# === Node.js ===
# 删除当前项目 node_modules
rm -rf node_modules

# 删除工作区所有 node_modules
find ~/workspace -name "node_modules" -type d -prune -exec rm -rf {} +

# === 通用 ===
# 删除所有 .DS_Store
find . -name ".DS_Store" -delete

# 删除空目录
find . -type d -empty -delete

# 查看磁盘使用
du -sh */ | sort -rh
```
