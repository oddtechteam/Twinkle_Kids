"""ORM models. Import every model module here so Alembic autogenerate can see it."""

from app.infrastructure.db.base import Base
from app.infrastructure.db.models.catalog import (
    CategoryModel,
    ProductCategoryModel,
    ProductMediaModel,
    ProductModel,
    ProductVariantModel,
    SizeChartModel,
)
from app.infrastructure.db.models.commerce import (
    CartItemModel,
    CartModel,
    InventoryMovementModel,
    OrderItemModel,
    OrderModel,
    WhatsAppOrderRequestItemModel,
    WhatsAppOrderRequestModel,
)
from app.infrastructure.db.models.content import (
    CollectionModel,
    CollectionProductModel,
    HomepageSectionModel,
    HomepageSectionProductModel,
    NavigationItemModel,
    StoreSettingsModel,
    WebsitePageModel,
)
from app.infrastructure.db.models.identity import (
    AddressModel,
    AuditLogModel,
    PermissionModel,
    RoleModel,
    RolePermissionModel,
    UserModel,
    UserRoleModel,
    UserSessionModel,
)
from app.infrastructure.db.models.marketing import (
    BulkOrderInquiryModel,
    CouponModel,
    CouponRedemptionModel,
    ReviewModel,
    ShippingRuleModel,
)
from app.infrastructure.db.models.media import MediaAssetModel

__all__ = [
    "AddressModel",
    "AuditLogModel",
    "Base",
    "BulkOrderInquiryModel",
    "CartItemModel",
    "CartModel",
    "CategoryModel",
    "CollectionModel",
    "CollectionProductModel",
    "CouponModel",
    "CouponRedemptionModel",
    "HomepageSectionModel",
    "HomepageSectionProductModel",
    "InventoryMovementModel",
    "MediaAssetModel",
    "NavigationItemModel",
    "OrderItemModel",
    "OrderModel",
    "PermissionModel",
    "ProductCategoryModel",
    "ProductMediaModel",
    "ProductModel",
    "ProductVariantModel",
    "ReviewModel",
    "RoleModel",
    "RolePermissionModel",
    "ShippingRuleModel",
    "SizeChartModel",
    "StoreSettingsModel",
    "UserModel",
    "UserRoleModel",
    "UserSessionModel",
    "WebsitePageModel",
    "WhatsAppOrderRequestItemModel",
    "WhatsAppOrderRequestModel",
]
