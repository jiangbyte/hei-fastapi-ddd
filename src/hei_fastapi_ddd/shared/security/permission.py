""" Author: Charlie

权限检查工具：判定是否持有指定权限码或超级权限。
"""


class PermissionChecker:
    """权限判断工具类。"""

    @staticmethod
    def has_permission(permissions: list[str], permission_code: str) -> bool:
        """是否命中指定权限码，或持有超级权限 ``*:*:*``。"""
        return permission_code in permissions or "*:*:*" in permissions
