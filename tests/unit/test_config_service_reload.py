""" Author: Charlie

配置保存后立即重载：验证请求事务未提交时 batch_save 仍能刷新内存快照。
"""

from sqlalchemy import select

from hei_fastapi_ddd.contexts.sys.api.config_schemas import (
    ConfigBatchItem,
    ConfigBatchSaveRequest,
)
from hei_fastapi_ddd.contexts.sys.application.config.config_application_service import ConfigService
from hei_fastapi_ddd.shared.config.reader import config_reader
from hei_fastapi_ddd.shared.id_generator.snowflake import generate_snowflake_id
from hei_fastapi_ddd.shared.persistence.models.sys_config import SysConfig


async def test_batch_save_reloads_config_before_request_transaction_commits(db_session):
    """鉴权等查询触发 autobegin 后，batch_save 仍应立即刷新 config_reader。"""
    original_engine = config_reader.get("DEFAULT_FILE_ENGINE")
    row = (
        await db_session.execute(
            select(SysConfig).where(SysConfig.config_key == "DEFAULT_FILE_ENGINE")
        )
    ).scalar_one_or_none()
    if row is None:
        db_session.add(
            SysConfig(
                id=generate_snowflake_id(),
                config_key="DEFAULT_FILE_ENGINE",
                config_value="RUSTFS",
                category="STORAGE",
            )
        )
        await db_session.commit()
    else:
        row.config_value = "RUSTFS"
        await db_session.commit()

    await config_reader.load_all()
    assert config_reader.get("DEFAULT_FILE_ENGINE") == "RUSTFS"

    try:
        # 模拟请求内鉴权等只读查询已开启外层事务。
        await db_session.execute(select(SysConfig).limit(1))

        await ConfigService(db_session).batch_save(
            ConfigBatchSaveRequest(
                items=[
                    ConfigBatchItem(
                        config_key="DEFAULT_FILE_ENGINE",
                        config_value="MINIO",
                        category="STORAGE",
                    )
                ]
            )
        )

        assert config_reader.get("DEFAULT_FILE_ENGINE") == "MINIO"
        assert config_reader.get_default_storage() is not None
        assert config_reader.get_default_storage().provider.value == "minio"
    finally:
        if original_engine is not None:
            await ConfigService(db_session).batch_save(
                ConfigBatchSaveRequest(
                    items=[
                        ConfigBatchItem(
                            config_key="DEFAULT_FILE_ENGINE",
                            config_value=original_engine,
                            category="STORAGE",
                        )
                    ]
                )
            )
        else:
            entity = (
                await db_session.execute(
                    select(SysConfig).where(SysConfig.config_key == "DEFAULT_FILE_ENGINE")
                )
            ).scalar_one_or_none()
            if entity is not None:
                await db_session.delete(entity)
                await db_session.commit()
            await config_reader.load_all()
