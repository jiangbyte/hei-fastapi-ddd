""" Author: Charlie

文件管理 API 路由测试：使用内存假存储，不再依赖 LOCAL / public proxy。
"""

from __future__ import annotations

from hei_fastapi_ddd.contexts.iam.infrastructure.persistence.account_po import SysAccount
from hei_fastapi_ddd.shared.config.enums import AccountStatusEnum, AccountType, StorageProvider
from hei_fastapi_ddd.shared.config.settings import settings
from hei_fastapi_ddd.shared.deps.db import get_db_session
from hei_fastapi_ddd.shared.security.session import SessionPayload, session_store
from hei_fastapi_ddd.shared.storage.config import StorageConfig


class _MemoryStorage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.config = StorageConfig(
            id="memory",
            name="memory",
            provider=StorageProvider.MINIO,
            bucket="test",
            bucket_public=True,
            base_url="https://cdn.example.com",
            is_default=True,
        )

    def upload_bytes(self, object_name: str, content: bytes, content_type: str = "") -> str:
        self.objects[object_name] = content
        return self.get_object_url(object_name)

    def delete_object(self, object_name: str) -> None:
        self.objects.pop(object_name, None)

    def get_object_url(self, object_name: str) -> str:
        return f"https://cdn.example.com/{object_name}"

    def get_presigned_url(self, object_name: str) -> str:
        return f"https://cdn.example.com/{object_name}?X-Amz-Signature=test"

    def get_object_bytes(self, object_name: str) -> bytes:
        return self.objects[object_name]


async def _seed_admin(client, token: str, permissions: list[str]) -> None:
    override = client._transport.app.dependency_overrides[get_db_session]
    async for session in override():
        account = SysAccount(
            password_hash="hashed",
            account_type=AccountType.ADMIN.value,
            account_status=AccountStatusEnum.ENABLED.value,
        )
        session.add(account)
        await session.flush()
        await session_store.set(
            SessionPayload(
                token=token,
                account_id=account.id,
                account_type=AccountType.ADMIN.value,
                role_ids=[],
                dept_ids=[],
                group_ids=[],
                permission_keys=permissions,
                permission_grants=[],
            ),
            ttl_seconds=3600,
        )
        await session.commit()
        break


async def test_admin_file_upload_page_detail_update_delete(client, monkeypatch):
    storage = _MemoryStorage()
    monkeypatch.setattr(
        "hei_fastapi_ddd.contexts.sys.application.file.file_application_service.resolve_storage_config",
        lambda *a, **k: storage.config,
    )
    monkeypatch.setattr("hei_fastapi_ddd.contexts.sys.application.file.file_application_service.get_storage", lambda *a, **k: storage)
    monkeypatch.setattr(settings.storage, "provider", StorageProvider.MINIO)

    token = "admin-file-token"
    await _seed_admin(
        client,
        token,
        [
            "sys:file:upload",
            "sys:file:page",
            "sys:file:detail",
            "sys:file:update",
            "sys:file:delete",
            "sys:file:download",
            "sys:file:url",
        ],
    )
    headers = {"Authorization": token}

    upload_response = await client.post(
        "/api/v1/admin/sys/file/upload",
        headers=headers,
        files={"file": ("report.png", b"image-bytes", "image/png")},
    )
    assert upload_response.status_code == 200
    uploaded = upload_response.json()["data"]
    assert uploaded["original_name"] == "report.png"
    assert uploaded["content_type"] == "image/png"
    assert uploaded["url"].startswith("https://cdn.example.com/")
    assert uploaded["object_name"] in storage.objects

    page_response = await client.get(
        "/api/v1/admin/sys/file/page?current=1&size=20&original_name=report&content_type=image",
        headers=headers,
    )
    assert page_response.status_code == 200
    assert page_response.json()["data"]["total"] == "1"
    file_id = page_response.json()["data"]["records"][0]["id"]

    detail_response = await client.get(
        f"/api/v1/admin/sys/file/detail?id={file_id}",
        headers=headers,
    )
    assert detail_response.status_code == 200
    assert detail_response.json()["data"]["object_name"] == uploaded["object_name"]

    download_response = await client.get(
        f"/api/v1/admin/sys/file/download?id={file_id}",
        headers=headers,
    )
    assert download_response.status_code == 200
    assert download_response.content == b"image-bytes"
    assert "attachment" in download_response.headers.get("content-disposition", "")

    update_response = await client.post(
        "/api/v1/admin/sys/file/update",
        headers=headers,
        json={"id": file_id, "original_name": "renamed.png"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["data"] is None

    updated_detail_response = await client.get(
        f"/api/v1/admin/sys/file/detail?id={file_id}",
        headers=headers,
    )
    assert updated_detail_response.json()["data"]["original_name"] == "renamed.png"
    assert updated_detail_response.json()["data"]["object_name"] == uploaded["object_name"]

    delete_response = await client.post(
        "/api/v1/admin/sys/file/delete",
        headers=headers,
        json={"ids": [file_id]},
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["data"] is None
    assert uploaded["object_name"] not in storage.objects

    empty_page_response = await client.get(
        "/api/v1/admin/sys/file/page?current=1&size=20&original_name=renamed",
        headers=headers,
    )
    assert empty_page_response.json()["data"]["total"] == "0"
