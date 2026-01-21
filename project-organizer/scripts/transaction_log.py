#!/usr/bin/env python3
"""
事务日志系统 - 确保所有文件操作可追踪、可恢复。

设计原则：
1. 每个操作在执行前记录 PENDING 状态
2. 操作成功后更新为 COMPLETED 状态
3. 任何时刻都可以从日志重建状态
4. 支持生成回滚脚本
"""

import json
import os
import hashlib
import shutil
import subprocess
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any


class OperationStatus(Enum):
    PENDING = "pending"          # 计划执行
    COPYING = "copying"          # 正在复制
    COPIED = "copied"            # 复制完成，等待验证
    VERIFIED = "verified"        # 验证通过，源可删除
    CLEANED = "cleaned"          # 源已删除
    FAILED = "failed"            # 操作失败
    ROLLED_BACK = "rolled_back"  # 已回滚


class OperationType(Enum):
    MOVE = "move"
    COPY = "copy"
    DELETE = "delete"
    MKDIR = "mkdir"


@dataclass
class Operation:
    """单个文件操作的记录"""
    id: str
    op_type: str  # OperationType value
    source: str
    target: str
    status: str = "pending"  # OperationStatus value
    size_kb: Optional[int] = None
    file_count: Optional[int] = None
    source_checksum: Optional[str] = None
    target_checksum: Optional[str] = None
    reason: str = ""
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "Operation":
        return cls(**data)


@dataclass
class Session:
    """一个整理会话，包含多个操作"""
    session_id: str
    created_at: str
    target_root: str
    status: str = "active"
    operations: List[Operation] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    protected_skipped: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        d = asdict(self)
        d["operations"] = [op.to_dict() for op in self.operations]
        return d

    @classmethod
    def from_dict(cls, data: Dict) -> "Session":
        ops = [Operation.from_dict(op) for op in data.pop("operations", [])]
        return cls(**data, operations=ops)


class TransactionLog:
    """事务日志管理器"""

    BASE_DIR = Path.home() / ".root-organizer"
    SESSIONS_DIR = BASE_DIR / "sessions"

    def __init__(self, session_id: Optional[str] = None):
        self.BASE_DIR.mkdir(parents=True, exist_ok=True)
        self.SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

        if session_id:
            self.session_id = session_id
            self.session = self._load_session()
        else:
            self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.session = Session(
                session_id=self.session_id,
                created_at=datetime.now().isoformat(),
                target_root=str(Path.home())
            )

        self.session_dir = self.SESSIONS_DIR / self.session_id
        self.session_dir.mkdir(parents=True, exist_ok=True)

    @property
    def log_file(self) -> Path:
        return self.session_dir / "transaction.log"

    @property
    def session_file(self) -> Path:
        return self.session_dir / "session.json"

    @property
    def rollback_file(self) -> Path:
        return self.session_dir / "rollback.sh"

    @property
    def checksums_file(self) -> Path:
        return self.session_dir / "checksums.json"

    def _load_session(self) -> Session:
        """从文件加载会话"""
        session_file = self.SESSIONS_DIR / self.session_id / "session.json"
        if session_file.exists():
            with open(session_file) as f:
                return Session.from_dict(json.load(f))
        raise FileNotFoundError(f"Session not found: {self.session_id}")

    def save(self) -> None:
        """保存会话状态"""
        with open(self.session_file, "w") as f:
            json.dump(self.session.to_dict(), f, indent=2, ensure_ascii=False)
        self._append_log(f"SESSION_SAVED at {datetime.now().isoformat()}")

    def _append_log(self, message: str) -> None:
        """追加日志条目"""
        timestamp = datetime.now().isoformat()
        with open(self.log_file, "a") as f:
            f.write(f"[{timestamp}] {message}\n")

    def add_operation(self, op: Operation) -> None:
        """添加一个操作到会话"""
        self.session.operations.append(op)
        self._append_log(f"OP_ADDED {op.id}: {op.op_type} {op.source} -> {op.target}")
        self.save()

    def update_operation_status(self, op_id: str, status: OperationStatus,
                                 error: Optional[str] = None) -> None:
        """更新操作状态"""
        for op in self.session.operations:
            if op.id == op_id:
                op.status = status.value
                if error:
                    op.error = error
                if status == OperationStatus.COPYING:
                    op.started_at = datetime.now().isoformat()
                elif status in (OperationStatus.VERIFIED, OperationStatus.FAILED,
                               OperationStatus.CLEANED):
                    op.completed_at = datetime.now().isoformat()
                break

        self._append_log(f"OP_STATUS {op_id}: {status.value}" +
                        (f" ERROR: {error}" if error else ""))
        self.save()

    def set_checksum(self, op_id: str, source_checksum: str = None,
                     target_checksum: str = None) -> None:
        """设置校验和"""
        for op in self.session.operations:
            if op.id == op_id:
                if source_checksum:
                    op.source_checksum = source_checksum
                if target_checksum:
                    op.target_checksum = target_checksum
                break
        self.save()

    def get_operation(self, op_id: str) -> Optional[Operation]:
        """获取单个操作"""
        for op in self.session.operations:
            if op.id == op_id:
                return op
        return None

    def get_pending_operations(self) -> List[Operation]:
        """获取待执行的操作"""
        return [op for op in self.session.operations
                if op.status == OperationStatus.PENDING.value]

    def get_reversible_operations(self) -> List[Operation]:
        """获取可回滚的操作（已复制但源未删除）"""
        return [op for op in self.session.operations
                if op.status in (OperationStatus.COPIED.value,
                                OperationStatus.VERIFIED.value)]

    def get_cleanup_candidates(self) -> List[Operation]:
        """获取可清理的操作（已验证，源可删除）"""
        return [op for op in self.session.operations
                if op.status == OperationStatus.VERIFIED.value]

    @classmethod
    def list_sessions(cls) -> List[Dict]:
        """列出所有会话"""
        sessions = []
        if not cls.SESSIONS_DIR.exists():
            return sessions

        for session_dir in sorted(cls.SESSIONS_DIR.iterdir(), reverse=True):
            if not session_dir.is_dir():
                continue
            session_file = session_dir / "session.json"
            if session_file.exists():
                try:
                    with open(session_file) as f:
                        data = json.load(f)
                    sessions.append({
                        "session_id": data["session_id"],
                        "created_at": data["created_at"],
                        "status": data.get("status", "unknown"),
                        "operation_count": len(data.get("operations", [])),
                        "has_rollback": (session_dir / "rollback.sh").exists()
                    })
                except Exception:
                    pass
        return sessions


def calculate_dir_checksum(path: Path, quick: bool = True) -> str:
    """
    计算目录的校验和。

    quick=True: 只统计文件数量和总大小（快速）
    quick=False: 计算所有文件的 MD5（慢但精确）
    """
    if not path.exists():
        return "NOT_EXISTS"

    if path.is_file():
        if quick:
            stat = path.stat()
            return f"FILE:{stat.st_size}:{stat.st_mtime}"
        else:
            h = hashlib.md5()
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    h.update(chunk)
            return h.hexdigest()

    # 目录
    file_count = 0
    total_size = 0

    for root, dirs, files in os.walk(path):
        # 跳过隐藏目录和常见缓存
        dirs[:] = [d for d in dirs if not d.startswith(".") and
                   d not in ("__pycache__", "node_modules", ".git")]
        for f in files:
            if f.startswith("."):
                continue
            try:
                fp = Path(root) / f
                stat = fp.stat()
                file_count += 1
                total_size += stat.st_size
            except (OSError, IOError):
                pass

    return f"DIR:{file_count}:{total_size}"


def verify_copy(source: Path, target: Path, quick: bool = True) -> tuple[bool, str]:
    """
    验证复制是否成功。

    Returns:
        (success, message)
    """
    if not target.exists():
        return False, f"Target does not exist: {target}"

    source_check = calculate_dir_checksum(source, quick)
    target_check = calculate_dir_checksum(target, quick)

    if source_check == target_check:
        return True, f"Checksum match: {source_check}"

    # 提取详细信息进行比较
    if source_check.startswith("DIR:") and target_check.startswith("DIR:"):
        s_parts = source_check.split(":")
        t_parts = target_check.split(":")
        s_count, s_size = int(s_parts[1]), int(s_parts[2])
        t_count, t_size = int(t_parts[1]), int(t_parts[2])

        if t_count >= s_count and t_size >= s_size:
            # 目标包含更多文件（可能之前存在），认为成功
            return True, f"Target has {t_count} files ({t_size} bytes), source has {s_count} files ({s_size} bytes)"

        return False, f"File count/size mismatch: source={s_count}/{s_size}, target={t_count}/{t_size}"

    return False, f"Checksum mismatch: source={source_check}, target={target_check}"


def rsync_copy(source: Path, target: Path, dry_run: bool = False) -> tuple[bool, str]:
    """
    使用 rsync 复制文件/目录。

    Returns:
        (success, output)
    """
    if not shutil.which("rsync"):
        # Fallback to shutil
        try:
            if source.is_dir():
                shutil.copytree(source, target, dirs_exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
            return True, "Copied using shutil"
        except Exception as e:
            return False, str(e)

    # 使用 rsync
    cmd = ["rsync", "-avh", "--progress"]
    if dry_run:
        cmd.append("--dry-run")

    # 确保目录复制正确（源路径末尾不加 /，目标是父目录）
    src_str = str(source)
    if source.is_dir():
        src_str = src_str.rstrip("/") + "/"
        target.mkdir(parents=True, exist_ok=True)
        dst_str = str(target) + "/"
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        dst_str = str(target)

    cmd.extend([src_str, dst_str])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return True, result.stdout
        else:
            return False, result.stderr
    except Exception as e:
        return False, str(e)


if __name__ == "__main__":
    # 简单测试
    print("Transaction Log Module")
    print(f"Sessions directory: {TransactionLog.SESSIONS_DIR}")
    print(f"Existing sessions: {TransactionLog.list_sessions()}")
