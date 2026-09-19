"""biz 限界上下文依赖装配。"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from hei_fastapi_ddd.contexts.biz.application.cg_test_activity.cg_test_activity_application_service import (
    CgTestActivityService,
)
from hei_fastapi_ddd.contexts.biz.application.cg_test_catalog.cg_test_catalog_application_service import (
    CgTestCatalogService,
)
from hei_fastapi_ddd.contexts.biz.application.cg_test_knowledge_category.cg_test_knowledge_category_application_service import (
    CgTestKnowledgeCategoryService,
    CgTestKnowledgeDocService,
)
from hei_fastapi_ddd.contexts.biz.application.cg_test_order.cg_test_order_application_service import (
    CgTestOrderItemService,
    CgTestOrderService,
)
from hei_fastapi_ddd.contexts.biz.infrastructure.persistence.cg_test_activity_repository import (
    CgTestActivityRepositoryImpl,
)
from hei_fastapi_ddd.contexts.biz.infrastructure.persistence.cg_test_catalog_repository import (
    CgTestCatalogRepositoryImpl,
)
from hei_fastapi_ddd.contexts.biz.infrastructure.persistence.cg_test_knowledge_category_repository import (
    CgTestKnowledgeCategoryRepositoryImpl,
    CgTestKnowledgeDocRepositoryImpl,
)
from hei_fastapi_ddd.contexts.biz.infrastructure.persistence.cg_test_order_repository import (
    CgTestOrderItemRepositoryImpl,
    CgTestOrderRepositoryImpl,
)
from hei_fastapi_ddd.shared.deps.db import get_db_session


def get_cg_test_activity_service(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> CgTestActivityService:
    return CgTestActivityService(db, CgTestActivityRepositoryImpl(db))


def get_cg_test_catalog_service(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> CgTestCatalogService:
    return CgTestCatalogService(db, CgTestCatalogRepositoryImpl(db))


def get_cg_test_order_service(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> CgTestOrderService:
    return CgTestOrderService(db, CgTestOrderRepositoryImpl(db))


def get_cg_test_order_item_service(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> CgTestOrderItemService:
    return CgTestOrderItemService(db, CgTestOrderItemRepositoryImpl(db))


def get_cg_test_knowledge_category_service(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> CgTestKnowledgeCategoryService:
    return CgTestKnowledgeCategoryService(db, CgTestKnowledgeCategoryRepositoryImpl(db))


def get_cg_test_knowledge_doc_service(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> CgTestKnowledgeDocService:
    return CgTestKnowledgeDocService(db, CgTestKnowledgeDocRepositoryImpl(db))
