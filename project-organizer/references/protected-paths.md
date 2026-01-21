# 受保护路径

这些路径在自动化整理时会被**跳过**，确保系统稳定性和开发环境完整性。

## 系统路径（绝对禁止）

| 路径 | 说明 |
|------|------|
| `/System` | macOS 系统文件 |
| `/bin`, `/sbin` | 系统二进制文件 |
| `/usr` | Unix 系统资源 |
| `/etc` | 系统配置 |
| `/var` | 可变数据 |
| `/opt` | 可选软件 |
| `/Library` | 系统级库 |
| `/Applications` | 系统应用 |
| `/Volumes` | 挂载卷 |

## 用户路径（默认保护）

### 包管理/工具链

| 路径 | 说明 |
|------|------|
| `~/.pyenv` | Python 版本管理 |
| `~/.asdf` | 多语言版本管理 |
| `~/.nvm` | Node.js 版本管理 |
| `~/.rbenv` | Ruby 版本管理 |
| `~/.cargo` | Rust 包管理 |
| `~/.rustup` | Rust 工具链 |
| `~/go` | Go 工作区 |
| `~/miniconda3`, `~/anaconda3` | Conda 环境 |

### Shell/配置

| 路径 | 说明 |
|------|------|
| `~/.zshrc`, `~/.bashrc` | Shell 配置 |
| `~/.bash_profile`, `~/.profile` | 登录配置 |
| `~/.config` | XDG 配置目录 |
| `~/.ssh` | SSH 密钥和配置 |
| `~/.gnupg` | GPG 密钥 |
| `~/.local` | 用户本地数据 |

### 应用数据

| 路径 | 说明 |
|------|------|
| `~/Library` | macOS 用户库（缓存、偏好设置等） |
| `~/.docker` | Docker 配置 |
| `~/.vscode` | VS Code 配置 |
| `~/.oh-my-zsh` | Oh My Zsh |
| `~/.vim`, `~/.emacs.d` | 编辑器配置 |

## 云盘路径（需暂停同步）

| 标记 | 服务 |
|------|------|
| `Mobile Documents` | iCloud Drive |
| `OneDrive` | Microsoft OneDrive |
| `Dropbox` | Dropbox |
| `Google Drive`, `gdrive` | Google Drive |

**重要**：在云盘路径中进行大量文件操作前，应：
1. 暂停云盘同步客户端
2. 或将文件先移出云盘到本地非同步目录

## Dotfiles 处理策略

所有以 `.` 开头的文件/目录默认被标记为 `protected` 或 `dotfile`：

- **已知保护路径**（如 `.config`, `.ssh`）→ 完全跳过
- **其他 dotfiles**（如 `.myapp`）→ 标记为 `dotfile`，建议保留原位

## 自定义保护

可在配置文件 `~/.root-organizer/config.json` 中添加自定义保护路径：

```json
{
  "custom_protected": [
    "~/my-special-folder",
    "~/important-data"
  ]
}
```

## 操作前检查清单

在整理任何路径前，工具会自动检查：

- [ ] 是否在系统路径列表中
- [ ] 是否是包管理器/工具链目录
- [ ] 是否包含 `node_modules`、`.venv` 等依赖目录
- [ ] 是否是 dotfile/dotdir
- [ ] 是否在云盘同步路径中
- [ ] 是否出现在 `$PATH`、`$PYTHONPATH` 等环境变量中

只有通过所有检查的路径才会被纳入整理计划。
