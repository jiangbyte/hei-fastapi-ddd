""" Author: Charlie

触发时间工具：校验 CRON / FIXED 配置并计算下次执行时间（对齐 hei-boot JobCronUtil）。
"""

from datetime import UTC, datetime, timedelta

from croniter import croniter

from hei_fastapi_ddd.types.business import BusinessError

TYPE_CRON = "CRON"
TYPE_FIXED = "FIXED"

_FIXED_MIN_INTERVAL_SECONDS = 1


def validate(trigger_type: str, trigger_config: str) -> None:
    """校验触发配置合法，非法时抛出 BusinessError。"""
    trigger_type = trigger_type.upper()
    trigger_config = (trigger_config or "").strip()
    if trigger_type == TYPE_FIXED:
        if not trigger_config.isdigit() or int(trigger_config) < _FIXED_MIN_INTERVAL_SECONDS:
            raise BusinessError("FIXED 触发配置必须为正整数秒数")
        return
    if trigger_type == TYPE_CRON:
        _validate_cron(trigger_config)
        return
    raise BusinessError(f"不支持的触发类型: {trigger_type}")


def compute_next_run_time(
    trigger_type: str, trigger_config: str, from_time: datetime
) -> datetime:
    """计算 from_time 之后的下一次执行时间。"""
    trigger_type = trigger_type.upper()
    trigger_config = (trigger_config or "").strip()
    if trigger_type == TYPE_FIXED:
        return from_time + timedelta(seconds=int(trigger_config))
    return _next_cron(trigger_config, from_time)


def _validate_cron(expr: str) -> None:
    """CRON 表达式必须可解析且未来存在可执行时间。

    Spring/hei-boot 语义：6 段时秒在首位（sec min hour dom mon dow），
    与 croniter 默认（秒在末尾）不同，故显式 second_at_beginning=True。
    """
    try:
        croniter(expr, datetime.now(UTC), second_at_beginning=True).get_next(datetime)
    except (ValueError, KeyError, OverflowError) as exc:
        raise BusinessError(f"CRON 表达式无效: {expr}") from exc


def _next_cron(expr: str, from_time: datetime) -> datetime:
    """取 from_time 之后的下一个匹配时间（Spring 语义，秒在首位）。"""
    try:
        return croniter(expr, from_time, second_at_beginning=True).get_next(datetime)
    except (ValueError, KeyError, OverflowError) as exc:
        raise BusinessError(f"CRON 表达式无效: {expr}") from exc
