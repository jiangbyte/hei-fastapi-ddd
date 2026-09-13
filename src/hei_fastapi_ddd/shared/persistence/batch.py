""" Author: Charlie

批量操作分批工具：对 IN 类查询按固定大小分批执行。

管理端批量接口的 ID 列表无上限，单条大 IN 会触发部分数据库
（如 MySQL max_allowed_packet）的绑定变量上限，
按固定大小分批可将单条语句规模控制在安全范围。
"""
from collections.abc import Iterator

BATCH_SIZE = 500


def chunked(items, size: int = BATCH_SIZE) -> Iterator[list]:
    """将可迭代对象按 size 分批，返回逐批列表（保持原始顺序）。"""
    batch = []
    for item in items:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch
