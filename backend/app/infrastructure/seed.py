"""Development-only demo catalogue (clearly labelled "[Demo]", slugs/SKUs prefixed "demo").

Goes through the real application commands so prices, variants and stock follow exactly the
same rules as admin edits. Safe to re-run: records are matched by slug and refreshed.
No user accounts or passwords are seeded.
"""

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.use_cases.catalog_admin import (
    CategoryCommands,
    CategoryInput,
    ProductCommands,
    ProductInput,
    VariantInput,
)
from app.domain.enums import ProductStatus
from app.infrastructure.db.models.catalog import CategoryModel, ProductModel
from app.infrastructure.db.repositories.catalog import (
    SqlAlchemyCategoryRepository,
    SqlAlchemyProductRepository,
)
from app.infrastructure.db.repositories.identity import SqlAlchemyAuditLogRepository
from app.infrastructure.db.repositories.inventory import SqlAlchemyInventoryLedger
from app.infrastructure.db.repositories.media import SqlAlchemyMediaAssetRepository
from app.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork

DEMO_PREFIX = "[Demo] "
LARGEST_SIZE_SURCHARGE = Decimal("50.00")

CATEGORIES: list[tuple[str, str, str | None, int]] = [
    # slug, name, parent slug, display order
    ("demo-girls", "Girls", None, 1),
    ("demo-boys", "Boys", None, 2),
    ("demo-baby", "Baby", None, 3),
    ("demo-girls-party-wear", "Party Wear", "demo-girls", 1),
]

SIZES = ["2-3Y", "3-4Y", "4-5Y", "5-6Y"]

# slug, name, sku, selling, original (MRP), categories, colours, description
PRODUCTS: list[tuple[str, str, str, str, str | None, list[str], list[str], str]] = [
    (
        "demo-blush-ruffle-party-dress",
        "Blush Ruffle Party Dress",
        "DEMO-DRS-001",
        "399.00",
        "599.00",
        ["demo-girls", "demo-girls-party-wear"],
        ["Blush"],
        "Tiered tulle dress with a soft cotton lining for twirls without the itch.",
    ),
    (
        "demo-navy-star-cotton-tee",
        "Navy Star Cotton Tee",
        "DEMO-TEE-002",
        "299.00",
        "449.00",
        ["demo-boys"],
        ["Navy", "Ivory"],
        "Breathable cotton tee with a hand-drawn star print.",
    ),
    (
        "demo-coral-twirl-frock",
        "Coral Twirl Frock",
        "DEMO-FRK-003",
        "549.00",
        None,  # no MRP: no discount is shown
        ["demo-girls"],
        ["Coral"],
        "A full-skirted everyday frock in breathable cotton.",
    ),
    (
        "demo-ivory-knit-romper",
        "Ivory Knit Romper",
        "DEMO-RMP-004",
        "699.00",
        "999.00",
        ["demo-baby"],
        ["Ivory"],
        "Soft knit romper with easy snap buttons.",
    ),
    (
        "demo-gold-sparkle-skirt",
        "Gold Sparkle Skirt",
        "DEMO-SKT-005",
        "449.00",
        "449.00",  # MRP equals selling price: valid, but no discount
        ["demo-girls", "demo-girls-party-wear"],
        ["Gold"],
        "Shimmering party skirt with an elastic waist.",
    ),
    (
        "demo-denim-dungaree-set",
        "Denim Dungaree Set",
        "DEMO-DNG-006",
        "849.00",
        "1299.00",
        ["demo-boys"],
        ["Denim Blue"],
        "Two-piece dungaree set with a striped tee.",
    ),
]


@dataclass(frozen=True, slots=True)
class SeedResult:
    categories: int
    products: int
    created: int
    updated: int


def _variants(
    sku: str, colours: list[str], selling: str, original: str | None
) -> list[VariantInput]:
    variants: list[VariantInput] = []
    for colour in colours:
        for index, size in enumerate(SIZES):
            # The largest size costs a little more (selling price and MRP alike), which
            # demonstrates variant-level overrides of both prices.
            largest = index == len(SIZES) - 1
            variants.append(
                VariantInput(
                    sku=f"{sku}-{colour[:3].upper()}-{size.replace('-', '')}",
                    size=size,
                    colour=colour,
                    selling_price_override=(
                        Decimal(selling) + LARGEST_SIZE_SURCHARGE if largest else None
                    ),
                    original_price_override=(
                        Decimal(original) + LARGEST_SIZE_SURCHARGE if largest and original else None
                    ),
                    stock_quantity=0 if index == 0 and colour == colours[0] else 12,
                )
            )
    return variants


def seed_demo_catalog(session: Session) -> SeedResult:
    def category_commands() -> CategoryCommands:
        return CategoryCommands(
            categories=SqlAlchemyCategoryRepository(session),
            products=SqlAlchemyProductRepository(session),
            media=SqlAlchemyMediaAssetRepository(session),
            audit=SqlAlchemyAuditLogRepository(session),
            uow=SqlAlchemyUnitOfWork(session),
        )

    def product_commands() -> ProductCommands:
        return ProductCommands(
            products=SqlAlchemyProductRepository(session),
            categories=SqlAlchemyCategoryRepository(session),
            media=SqlAlchemyMediaAssetRepository(session),
            inventory=SqlAlchemyInventoryLedger(session),
            audit=SqlAlchemyAuditLogRepository(session),
            uow=SqlAlchemyUnitOfWork(session),
        )

    created = updated = 0
    category_ids: dict[str, UUID] = {}
    for slug, name, parent_slug, order in CATEGORIES:
        category = CategoryInput(
            name=DEMO_PREFIX + name,
            slug=slug,
            parent_id=category_ids.get(parent_slug) if parent_slug else None,
            display_order=order,
            custom_product_ordering=slug == "demo-girls",
            description=f"Demonstration category: {name}.",
        )
        existing = session.scalar(select(CategoryModel.id).where(CategoryModel.slug == slug))
        if existing is None:
            category_ids[slug] = category_commands().create(category, actor_id=None)
            created += 1
        else:
            category_commands().update(existing, category, actor_id=None)
            category_ids[slug] = existing
            updated += 1

    for slug, name, sku, selling, original, categories, colours, description in PRODUCTS:
        product = ProductInput(
            name=DEMO_PREFIX + name,
            slug=slug,
            sku=sku,
            selling_price=Decimal(selling),
            original_price=Decimal(original) if original else None,
            status=ProductStatus.ACTIVE,
            short_description=description,
            description=description + " This is demonstration data.",
            category_ids=[category_ids[c] for c in categories],
            variants=_variants(sku, colours, selling, original),
            seo_title=f"{name} | Twinkle Kids (demo)",
        )
        existing = session.scalar(select(ProductModel.id).where(ProductModel.slug == slug))
        if existing is None:
            product_commands().create(product, actor_id=None)
            created += 1
        else:
            product_commands().update(existing, product, actor_id=None)
            updated += 1

    return SeedResult(
        categories=len(CATEGORIES), products=len(PRODUCTS), created=created, updated=updated
    )
