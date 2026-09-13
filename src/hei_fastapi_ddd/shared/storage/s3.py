""" Author: Charlie

S3 兼容存储：基于 boto3 的通用引擎，以及 MinIO/RustFS 的差异化子类。
公开桶返回永久直链；私有桶返回预签名 URL（对齐 hei-boot S3StorageService.publicUrl）。
"""

from dataclasses import replace
from urllib.parse import urlparse, urlunparse

import boto3
from botocore.client import Config

from hei_fastapi_ddd.shared.storage.config import StorageConfig
from hei_fastapi_ddd.shared.storage.url import quote_object_name


class S3CompatibleStorage:
    """S3 兼容存储基类，通过 boto3 访问对象。"""

    def __init__(self, config: StorageConfig, *, force_path_style: bool | None = None) -> None:
        self.config = config
        self.bucket = config.bucket
        self.force_path_style = (
            config.force_path_style if force_path_style is None else force_path_style
        )
        endpoint = config.endpoint.rstrip("/")
        scheme = "https" if config.use_ssl else "http"
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            endpoint_url = endpoint
        else:
            endpoint_url = f"{scheme}://{endpoint}"
        self._endpoint_url = endpoint_url.rstrip("/")
        config_kwargs: dict = {"signature_version": "s3v4"}
        if self.force_path_style:
            config_kwargs["s3"] = {"addressing_style": "path"}
        client_config = Config(**config_kwargs)
        self.client = boto3.client(
            "s3",
            endpoint_url=self._endpoint_url,
            aws_access_key_id=config.access_key,
            aws_secret_access_key=config.secret_key,
            region_name=config.region or None,
            config=client_config,
        )

    def upload_bytes(
        self,
        object_name: str,
        content: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        """上传字节内容并返回对象公开 URL。"""
        self.client.put_object(
            Bucket=self.bucket,
            Key=object_name,
            Body=content,
            ContentType=content_type,
        )
        return self.get_object_url(object_name)

    def delete_object(self, object_name: str) -> None:
        """删除对象。"""
        self.client.delete_object(Bucket=self.bucket, Key=object_name)

    def get_object_url(self, object_name: str) -> str:
        """公开桶→永久直链；私有桶→预签名 GET。"""
        if self.config.bucket_public:
            return self._build_public_direct_url(object_name)
        return self.get_presigned_url(object_name)

    def get_presigned_url(self, object_name: str) -> str:
        """生成 GET 签名 URL。"""
        expire = self.config.presign_expire_seconds or 3600
        if expire <= 0:
            expire = 3600
        return str(
            self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": object_name},
                ExpiresIn=expire,
            )
        )

    def get_object_bytes(self, object_name: str) -> bytes:
        """下载对象字节内容（供鉴权下载接口返回）。"""
        response = self.client.get_object(Bucket=self.bucket, Key=object_name)
        try:
            return response["Body"].read()
        finally:
            response["Body"].close()

    def _build_public_direct_url(self, object_name: str) -> str:
        """公开桶永久 URL：优先 base_url，否则 endpoint + bucket。"""
        encoded = quote_object_name(object_name)
        base = (self.config.base_url or "").strip().rstrip("/")
        if base:
            return f"{base}/{encoded}"
        if not self.bucket or not self._endpoint_url:
            raise RuntimeError("S3 bucket/endpoint is required for public URL")
        if self.force_path_style:
            return f"{self._endpoint_url}/{self.bucket}/{encoded}"
        parsed = urlparse(self._endpoint_url)
        host = parsed.netloc
        if not host:
            return f"{self._endpoint_url}/{self.bucket}/{encoded}"
        scheme = parsed.scheme or ("https" if self.config.use_ssl else "http")
        return urlunparse((scheme, f"{self.bucket}.{host}", f"/{encoded}", "", "", ""))


class MinioStorage(S3CompatibleStorage):
    """MinIO 存储引擎，强制 path-style 寻址。"""

    def __init__(self, config: StorageConfig) -> None:
        super().__init__(config, force_path_style=True)


class RustFSStorage(S3CompatibleStorage):
    """RustFS：S3 兼容，默认 path-style；region 缺省 us-east-1。"""

    def __init__(self, config: StorageConfig) -> None:
        region = (config.region or "").strip() or "us-east-1"
        if region != config.region:
            config = replace(config, region=region)
        super().__init__(config, force_path_style=True)
