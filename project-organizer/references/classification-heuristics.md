# 分类启发与目标建议

自动化分类系统根据文件/目录名称、后缀、修改时间等特征进行分类，并建议目标位置。

## 分类标签

| 标签 | 说明 | 默认操作 |
|------|------|----------|
| `protected` | 系统/工具链路径 | 跳过 |
| `dotfile` | 非保护的 dotfile | 保留原位 |
| `downloads` | 下载目录 | 清理或归档 |
| `user_media` | 用户媒体目录 | 保留原位 |
| `workspace` | 工作区/项目目录 | 保留原位 |
| `virtualenv` | Python 虚拟环境 | 保留（与项目同级） |
| `node_modules` | Node.js 依赖 | 保留（与项目同级） |
| `cache_tmp` | 缓存/临时文件 | 可清理 |
| `installer_archive` | 安装包/归档文件 | 移到 `~/installers` |
| `media` | 媒体文件 | 移到 `~/media` |
| `other` | 未分类 | 需人工审查 |

## 分类规则详情

### 精确名称匹配（置信度 95%）

```python
"downloads": ["downloads", "download", "下载"]
"user_media": ["desktop", "documents", "pictures", "movies", "music", "桌面", "文档", "图片"]
"workspace": ["workspace", "projects", "code", "src", "dev", "repos", "github"]
"virtualenv": ["venv", ".venv", "env", "envs", "virtualenv"]
"cache_tmp": ["cache", "caches", "tmp", "temp", "logs", "log"]
```

### 后缀匹配（置信度 90%）

```python
"installer_archive": [".dmg", ".pkg", ".iso", ".zip", ".tar", ".tar.gz", ".rar", ".7z", ".exe", ".msi"]
"media": [".mp3", ".mp4", ".mkv", ".avi", ".mov", ".jpg", ".jpeg", ".png", ".gif", ".psd"]
"cache_tmp": [".log", ".tmp"]
```

### 包含匹配（置信度 70%）

```python
"workspace": ["project", "code"]
"virtualenv": ["venv"]
"cache_tmp": ["cache", "tmp", "temp", "log"]
```

### 前缀匹配（置信度 85%）

```python
"protected/dotfile": 以 "." 开头
```

## 推荐目录结构

```
~/
├── workspace/           # 活跃项目
│   ├── personal/
│   ├── work/
│   └── learning/
├── archive/             # 归档（按年份）
│   ├── 2024/
│   └── 2023/
├── installers/          # 安装包
│   └── deps/            # 依赖缓存（可选）
├── media/               # 媒体文件
│   ├── photos/
│   ├── videos/
│   └── music/
├── scratch/             # 临时/待整理
│   ├── downloads/       # 下载待分类
│   └── cache/           # 应用缓存
└── sync/                # 云盘同步区
    ├── icloud/
    └── dropbox/
```

## 目标路径模板

| 源分类 | 目标模板 | 示例 |
|--------|----------|------|
| `installer_archive` (.dmg/.pkg) | `~/installers/{filename}` | `~/installers/VSCode.dmg` |
| `installer_archive` (.zip/.tar) | `~/archive/{year}/{name}` | `~/archive/2024/project.zip` |
| 超过 180 天未修改的目录 | `~/archive/{year}/{name}` | `~/archive/2024/old_project` |
| `downloads` 中的内容 | `~/scratch/downloads/` | - |
| `media` 文件 | `~/media/{type}/` | `~/media/photos/` |

## 置信度说明

| 置信度 | 含义 | 自动化建议 |
|--------|------|------------|
| 90-100% | 高度确定 | 可自动执行 |
| 70-89% | 较为确定 | 建议确认后执行 |
| 50-69% | 中等确定 | 需要人工审查 |
| < 50% | 低置信度 | 仅供参考 |

## 特殊处理

### 虚拟环境

- Python `.venv`/`venv`：应与项目保持同级
- 如果在根目录发现独立的虚拟环境，建议移到对应项目内

### Node Modules

- `node_modules` 不应移动
- 如果在非项目目录发现，可能是孤立依赖，可考虑删除

### 归档年龄阈值

默认将 **180 天**未修改的项目/文件标记为归档候选。可在配置文件中调整：

```json
{
  "archive_age_days": 180
}
```

## 自定义分类

在 `~/.root-organizer/config.json` 中添加自定义分类：

```json
{
  "custom_classifications": {
    "my_special_folder": "keep",
    "temp_data_*": "scratch"
  },
  "custom_targets": {
    "*.psd": "~/media/design/",
    "*.ai": "~/media/design/"
  }
}
```
