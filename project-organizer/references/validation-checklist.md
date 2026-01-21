# 验证清单

操作完成后，按此清单验证系统完整性。

## 自动化验证（由工具执行）

运行 `safe_executor.py verify --session <session_id>` 会自动检查：

- [x] 所有复制操作的文件数量/大小匹配
- [x] 目标路径存在且可访问
- [x] 事务日志状态一致性

## 手动验证（推荐）

### 1. Shell 环境

```bash
# 新开终端窗口，检查环境变量
echo $PATH
echo $PYTHONPATH
echo $GOPATH

# 检查常用命令
command -v zsh bash python python3 node npm brew git
```

**检查点：**
- [ ] PATH 中没有指向已移动路径的条目
- [ ] 常用命令都能正常找到

### 2. 包管理器健康

```bash
# Homebrew
brew doctor

# Python (选用)
pyenv versions
conda info --envs
pip list

# Node.js (选用)
nvm list
npm config get prefix
pnpm store status

# 其他 (选用)
asdf list
rbenv versions
```

**检查点：**
- [ ] 包管理器无报错
- [ ] 虚拟环境列表正确
- [ ] 全局包可访问

### 3. 软链完整性

```bash
# 查找断开的软链
find ~ -maxdepth 3 -xtype l -print 2>/dev/null

# 或指定范围
find ~/workspace -xtype l -print
```

**检查点：**
- [ ] 无意外断开的软链
- [ ] 必要时在旧位置创建指向新位置的软链

### 4. 应用程序

**检查点：**
- [ ] IDE/编辑器能打开最近项目
- [ ] 终端能 cd 到常用目录
- [ ] 开发服务器能正常启动

### 5. 云盘同步

```bash
# 检查 iCloud 状态（macOS）
brctl status

# 检查同步文件夹
ls -la ~/Library/Mobile\ Documents/
```

**检查点：**
- [ ] 云盘状态为"已完成同步"
- [ ] 无文件冲突提示
- [ ] 重要文件在云端有备份

### 6. 项目验证

选择 1-2 个代表性项目进行完整验证：

```bash
cd ~/workspace/my-project

# 安装依赖
npm install  # 或 pip install -r requirements.txt

# 运行测试
npm test  # 或 pytest

# 启动开发服务器
npm run dev  # 或 python manage.py runserver
```

**检查点：**
- [ ] 依赖安装成功
- [ ] 测试通过
- [ ] 服务能正常启动

## 回滚决策

如果发现问题，根据严重程度决定是否回滚：

| 问题类型 | 建议操作 |
|----------|----------|
| PATH 断开 | 修复 PATH 或创建软链 |
| 单个软链断开 | 创建新软链 |
| 包管理器报错 | 尝试修复，若失败则回滚 |
| 多个应用无法启动 | 执行回滚 |
| 数据丢失迹象 | **立即回滚** |

## 执行回滚

```bash
# 方式 1：使用工具
python safe_executor.py rollback --session <session_id>

# 方式 2：直接运行回滚脚本
bash ~/.root-organizer/sessions/<session_id>/rollback.sh
```

## 清理确认

验证通过后，才能安全清理源文件：

```bash
python safe_executor.py cleanup --session <session_id>
```

**重要**：
- 源文件删除后，回滚脚本仍然保留
- 但回滚将无法恢复已删除的源文件
- 建议保留会话目录至少 30 天

## 会话管理

```bash
# 查看所有会话
python safe_executor.py list-sessions

# 查看特定会话详情
cat ~/.root-organizer/sessions/<session_id>/session.json | jq

# 查看事务日志
cat ~/.root-organizer/sessions/<session_id>/transaction.log
```
