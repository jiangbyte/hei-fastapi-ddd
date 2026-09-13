""" Author: Charlie

阿里云 OSS 存储：基于 oss2 SDK 的上传、删除与签名 URL。
公开桶返回永久直链；私有桶返回预签名 URL（对齐 hei-boot）。
"""

from urllib.parse import urljoin

from hei_fastapi_ddd.shared.storage.config import StorageConfig
from hei_fastapi_ddd.shared.storage.url import quote_object_name


class OSSStorage:
    """阿里云 OSS 存储引擎。"""

    def __init__(self, config: StorageConfig) -> None:
        import oss2

        self.config = config
        endpoint = config.endpoint.rstrip("/")
        auth = oss2.Auth(config.access_key, config.secret_key)
        self.bucket_name = config.bucket
        self.bucket = oss2.Bucket(auth, endpoint, self.bucket_name)

    def upload_bytes(
        self,
        object_name: str,
        content: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        """上传字节内容并返回对象公开 URL。"""
        headers = {"Content-Type": content_type}
        self.bucket.put_object(object_name, content, headers=headers)
        return self.get_object_url(object_name)

    def delete_object(self, object_name: str) -> None:
        """删除对象。"""
        self.bucket.delete_object(object_name)

    def get_object_url(self, object_name: str) -> str:
        """公开桶→永久直链；私有桶→预签名 GET。"""
        if self.config.bucket_public:
            if self.config.base_url:
                return urljoin(
                    self.config.base_url.rstrip("/") + "/",
                    quote_object_name(object_name),
                )
            endpoint = self.config.endpoint.rstrip("/")
            if not endpoint.startswith("http://") and not endpoint.startswith("https://"):
                scheme = "https" if self.config.use_ssl else "http"
                endpoint = f"{scheme}://{endpoint}"
            return f"{endpoint.rstrip('/')}/{self.bucket_name}/{quote_object_name(object_name)}"
        return self.get_presigned_url(object_name)

    def get_presigned_url(self, object_name: str) -> str:
        """生成 GET 签名 URL。"""
        expire = self.config.presign_expire_seconds or 3600
        if expire <= 0:
            expire = 3600
        return str(self.bucket.sign_url("GET", object_name, expire))

    def get_object_bytes(self, object_name: str) -> bytes:
        """下载对象字节内容（供鉴权下载接口返回）。"""
        return self.bucket.get_object(object_name).read()
