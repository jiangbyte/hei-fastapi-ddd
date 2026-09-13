""" Author: Charlie

ORM 模型聚合入口：显式导入各上下文 infrastructure 层的 SQLAlchemy PO，
供 Alembic 与元数据扫描使用。
"""

# 平台级模型
from hei_fastapi_ddd.shared.persistence.models import sys_config as sys_config_model  # noqa: F401
from hei_fastapi_ddd.shared.persistence.models import (  # noqa: F401
    sys_weak_password as sys_weak_password_model,
)

# 业务上下文 PO
from hei_fastapi_ddd.contexts.auth.infrastructure.persistence import oauth_po as oauth_binding_model  # noqa: F401
from hei_fastapi_ddd.contexts.biz.infrastructure.persistence import (  # noqa: F401
    cg_test_activity_po as cg_test_activity_model,
)
from hei_fastapi_ddd.contexts.biz.infrastructure.persistence import (  # noqa: F401
    cg_test_catalog_po as cg_test_catalog_model,
)
from hei_fastapi_ddd.contexts.biz.infrastructure.persistence import (  # noqa: F401
    cg_test_knowledge_category_po as cg_test_knowledge_model,
)
from hei_fastapi_ddd.contexts.biz.infrastructure.persistence import (  # noqa: F401
    cg_test_order_po as cg_test_order_model,
)
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence import account_po as iam_account_model  # noqa: F401
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence import (  # noqa: F401
    password_history_po as iam_password_history_model,
)
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence import client_po as iam_client_model  # noqa: F401
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence import dept_po as iam_dept_model  # noqa: F401
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence import group_po as iam_group_model  # noqa: F401
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence import position_po as iam_position_model  # noqa: F401
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence import relation_po as iam_relation_model  # noqa: F401
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence import resource_po as iam_resource_model  # noqa: F401
from hei_fastapi_ddd.contexts.iam.infrastructure.persistence import role_po as iam_role_model  # noqa: F401
from hei_fastapi_ddd.contexts.profile.infrastructure.persistence import (  # noqa: F401
    admin_po as profile_admin_model,
)
from hei_fastapi_ddd.contexts.profile.infrastructure.persistence import (  # noqa: F401
    identity_po as profile_identity_model,
)
from hei_fastapi_ddd.contexts.profile.infrastructure.persistence import (  # noqa: F401
    portal_po as profile_portal_model,
)
from hei_fastapi_ddd.contexts.sys.infrastructure.persistence import (  # noqa: F401
    audit_alert_po as audit_alert_model,
)
from hei_fastapi_ddd.contexts.sys.infrastructure.persistence import audit_po as audit_model  # noqa: F401
from hei_fastapi_ddd.contexts.sys.infrastructure.persistence import (  # noqa: F401
    audit_outbox as audit_outbox_model,
)
from hei_fastapi_ddd.contexts.sys.infrastructure.persistence import banner_po as banner_model  # noqa: F401
from hei_fastapi_ddd.contexts.sys.infrastructure.persistence import codegen_po as codegen_model  # noqa: F401
from hei_fastapi_ddd.contexts.sys.infrastructure.persistence import dict_po as dict_model  # noqa: F401
from hei_fastapi_ddd.contexts.sys.infrastructure.persistence import feedback_po as feedback_model  # noqa: F401
from hei_fastapi_ddd.contexts.sys.infrastructure.persistence import file_po as file_model  # noqa: F401
from hei_fastapi_ddd.contexts.sys.infrastructure.persistence import job_po as job_model  # noqa: F401
from hei_fastapi_ddd.contexts.sys.infrastructure.persistence import notice_po as notice_model  # noqa: F401
from hei_fastapi_ddd.contexts.sys.infrastructure.persistence import workspace_po as workspace_model  # noqa: F401
