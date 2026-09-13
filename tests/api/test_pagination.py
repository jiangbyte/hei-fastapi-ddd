""" Author: Charlie """

from hei_fastapi_ddd.shared.config.enums import AccountStatusEnum, AccountType, StorageProvider
from hei_fastapi_ddd.shared.security.session import SessionPayload, session_store
from hei_fastapi_ddd.shared.storage.config import StorageConfig
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.account_po import SysAccount
from hei_fastapi_ddd.contexts.sys.infrastructure.persistence.file_po import SysFile


class _MemoryStorage:
    def __init__(self) -> None:
        self.config = StorageConfig(
            id="memory",
            name="memory",
            provider=StorageProvider.MINIO,
            bucket="test",
            bucket_public=True,
            base_url="https://cdn.example.com",
            is_default=True,
        )

    def get_object_url(self, object_name: str) -> str:
        return f"https://cdn.example.com/{object_name}"


async def test_admin_file_list_uses_current_size_total_pages_records(client, monkeypatch):
    storage = _MemoryStorage()
    monkeypatch.setattr(
        "hei_fastapi_ddd.contexts.sys.application.file.file_application_service.resolve_storage_config",
        lambda *a, **k: storage.config,
    )
    monkeypatch.setattr("hei_fastapi_ddd.contexts.sys.application.file.file_application_service.get_storage", lambda *a, **k: storage)

    override = client._transport.app.dependency_overrides
    get_db_session = next(iter(override))

    async for session in override[get_db_session]():
        account_id = "admin-pager-id"
        account = SysAccount(
            id=account_id,
            password_hash="hashed",
            account_type=AccountType.ADMIN.value,
            account_status=AccountStatusEnum.ENABLED.value,
        )
        file = SysFile(
            object_name="uploads/20260617/demo.txt",
            original_name="demo.txt",
            storage_provider="minio",
            bucket="test",
            content_type="text/plain",
            size=4,
            url="https://cdn.example.com/uploads/20260617/demo.txt",
            created_by=account_id,
        )
        session.add_all([account, file])
        await session.flush()
        await session_store.set(
            SessionPayload(
                token="admin-pagination-token",
                account_id=account_id,
                account_type=AccountType.ADMIN.value,
                role_ids=[],
                dept_ids=[],
                group_ids=[],
                permission_keys=["sys:file:page"],
                permission_grants=[],
            ),
            ttl_seconds=3600,
        )
        await session.commit()
        break

    response = await client.get(
        "/api/v1/admin/sys/file/page?current=1&size=20",
        headers={"Authorization": "admin-pagination-token"},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["current"] == "1"
    assert data["size"] == "20"
    assert data["total"] == "1"
    assert data["pages"] == "1"
    assert isinstance(data["records"], list)
    assert data["records"][0]["object_name"] == "uploads/20260617/demo.txt"
    assert "page" not in data
    assert "page_size" not in data
    assert "items" not in data
