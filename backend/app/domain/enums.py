"""Constrained status values. Stored as strings with matching DB CHECK constraints."""

from enum import StrEnum


class ProductStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class PublishStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"


class HomepageSectionType(StrEnum):
    HERO_BANNER = "hero_banner"
    CATEGORY_GRID = "category_grid"
    PRODUCT_CAROUSEL = "product_carousel"
    PRODUCT_GRID = "product_grid"
    EDITORIAL_BANNER = "editorial_banner"  # image + text
    PROMO_BANNER = "promo_banner"  # seasonal / festive banner
    COLLECTION_SHOWCASE = "collection_showcase"  # featured collections
    OCCASION_COLLECTION = "occasion_collection"  # one collection spotlight with its products
    TRUST_STRIP = "trust_strip"
    TESTIMONIALS = "testimonials"
    FAQ = "faq"
    ANNOUNCEMENT = "announcement"
    CONTACT = "contact"
    RICH_TEXT = "rich_text"


PRODUCT_SECTION_TYPES = frozenset(
    {
        HomepageSectionType.PRODUCT_CAROUSEL,
        HomepageSectionType.PRODUCT_GRID,
        HomepageSectionType.OCCASION_COLLECTION,
    }
)


class SelectionMode(StrEnum):
    NONE = "none"  # section shows no products (banners, rich text)
    MANUAL = "manual"  # homepage_section_products, ordered per section
    CATEGORY = "category"
    COLLECTION = "collection"
    NEWEST = "newest"


class NavigationMenu(StrEnum):
    HEADER = "header"
    FOOTER = "footer"
    MOBILE = "mobile"


class NavigationLinkType(StrEnum):
    CATEGORY = "category"
    COLLECTION = "collection"
    PAGE = "page"
    URL = "url"
    HEADING = "heading"  # group label (e.g. a footer column) with child links


class CartStatus(StrEnum):
    ACTIVE = "active"
    CONVERTED = "converted"
    ABANDONED = "abandoned"


class OrderStatus(StrEnum):
    """Internal, admin-only workflow states. Not exposed as a customer tracking timeline."""

    PENDING_CONFIRMATION = "pending_confirmation"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    PACKED = "packed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    RETURNED = "returned"


class PaymentStatus(StrEnum):
    """Manual payment bookkeeping only; no payment gateway is integrated."""

    UNPAID = "unpaid"
    PAID = "paid"
    PARTIALLY_REFUNDED = "partially_refunded"
    REFUNDED = "refunded"


class PaymentMethod(StrEnum):
    CASH_ON_DELIVERY = "cash_on_delivery"
    UPI_MANUAL = "upi_manual"
    BANK_TRANSFER = "bank_transfer"
    OTHER = "other"


class OrderSource(StrEnum):
    WEBSITE = "website"
    WHATSAPP = "whatsapp"
    ADMIN = "admin"


class WhatsAppRequestStatus(StrEnum):
    """`initiated` only means the customer was handed a WhatsApp link. It is NOT proof that a
    message was sent; staff move it to `contacted` after actually receiving the message."""

    INITIATED = "initiated"
    CONTACTED = "contacted"
    CONVERTED = "converted"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class InventoryReason(StrEnum):
    INITIAL_STOCK = "initial_stock"
    RESTOCK = "restock"
    ADJUSTMENT = "adjustment"
    ORDER_PLACED = "order_placed"
    ORDER_CANCELLED = "order_cancelled"
    RETURN = "return"
    DAMAGED = "damaged"


class DiscountType(StrEnum):
    PERCENTAGE = "percentage"
    FIXED_AMOUNT = "fixed_amount"


class ReviewStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class InquiryStatus(StrEnum):
    NEW = "new"
    CONTACTED = "contacted"
    QUOTED = "quoted"
    CLOSED = "closed"


def sql_in(enum: type[StrEnum]) -> str:
    """Render ``'a','b',...`` for CHECK constraints (values are fixed identifiers)."""
    return ",".join(f"'{member.value}'" for member in enum)
