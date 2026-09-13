""" Author: Charlie

按日轮转文件处理器——写入 logs/YYYY/MM/DD-{pid}.log。

支持按大小轮转；通过 PID 文件名实现多进程安全（无需文件锁）。
"""
import logging
import os
from datetime import datetime

from hei_fastapi_ddd.shared.config.settings import settings


class DailyFileHandler(logging.Handler):
    def __init__(self, log_dir: str | None = None) -> None:
        """初始化处理器：解析日志目录、单文件大小上限与进程 PID。"""
        super().__init__()
        self._log_dir = log_dir or settings.observability.log_dir
        self._max_bytes = settings.observability.log_file_max_mb * 1024 * 1024
        self._pid = os.getpid()
        self._formatter = None
        self._file = None
        self._current_path: str | None = None

    def emit(self, record: logging.LogRecord) -> None:
        """将日志记录写入当日文件。"""
        path = self._daily_path()
        if path != self._current_path:
            self._close()
            self._ensure_dir(path)
            self._current_path = path
            self._file = open(path, "a", encoding="utf-8")

        if self._file and self._check_rollover():
            self._close()
            self._rotate(path)
            self._ensure_dir(path)
            self._file = open(path, "a", encoding="utf-8")

        if self._file:
            try:
                msg = self.format(record)
                self._file.write(msg + "\n")
                self._file.flush()
            except Exception:
                self.handleError(record)

    def _daily_path(self) -> str:
        """构建当日日志文件路径。"""
        now = datetime.now()
        return os.path.join(
            self._log_dir,
            str(now.year),
            f"{now.month:02d}",
            f"{now.day:02d}-{self._pid}.log",
        )

    def _ensure_dir(self, path: str) -> None:
        """按需创建日志目录（失败静默，交由写文件阶段报错）。"""
        dirname = os.path.dirname(path)
        if not os.path.exists(dirname):
            try:
                os.makedirs(dirname, exist_ok=True)
            except OSError:
                pass

    def _check_rollover(self) -> bool:
        """检查当前文件是否超过最大大小。"""
        if not self._file:
            return False
        try:
            return self._file.tell() >= self._max_bytes
        except OSError:
            return False

    def _rotate(self, path: str) -> None:
        """将当前文件重命名为 .1、.2 等。"""
        counter = 1
        while os.path.exists(f"{path}.{counter}"):
            counter += 1
        try:
            os.rename(path, f"{path}.{counter}")
        except OSError:
            pass

    def _close(self) -> None:
        """关闭并清空当前文件句柄。"""
        if self._file:
            try:
                self._file.close()
            except OSError:
                pass
            self._file = None

    def close(self) -> None:
        """关闭文件句柄并执行标准 Handler 清理。"""
        self._close()
        super().close()
