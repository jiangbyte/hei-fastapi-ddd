"""Author: Charlie

实名认证枚举，对齐 hei-boot profile identity 模块。
"""

from enum import StrEnum


class IdentitySnapshotStatus(StrEnum):
    UNVERIFIED = "UNVERIFIED"
    VERIFIED = "VERIFIED"
    REVOKED = "REVOKED"


class RealNameCaseStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class RealNameBusinessType(StrEnum):
    ACCOUNT_VERIFY = "ACCOUNT_VERIFY"
    ACCOUNT_RECOVERY = "ACCOUNT_RECOVERY"


class VerifyChannel(StrEnum):
    MANUAL = "MANUAL"
    THIRD_PARTY = "THIRD_PARTY"
    EID = "EID"


DOCUMENT_TYPES = ("ID_CARD", "PASSPORT", "EID")
