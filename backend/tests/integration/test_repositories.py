"""Repository behaviour against a real database (SQLite here; Postgres in the live suite)."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.bootstrap import Container
from app.domain.entities.catalog import Category, Product, ProductMediaLink, ProductVariant
from app.domain.entities.identity import AuthSession, Role
from app.domain.entities.media import MediaAsset, MediaPurpose, MediaVisibility
from app.domain.enums import ProductStatus
from app.domain.errors import ConflictError
from app.domain.value_objects.pricing import PricePair
from app.infrastructure.db.models.catalog import ProductCategoryModel, ProductModel
from app.infrastructure.db.repositories.catalog import (
    SqlAlchemyCategoryRepository,
    SqlAlchemyCollectionRepository,
    SqlAlchemyProductRepository,
)
from app.infrastructure.db.repositories.identity import SqlAlchemySessionRepository
from app.infrastructure.db.repositories.media import SqlAlchemyMediaAssetRepository
from app.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from tests.conftest import create_user


def _category(name: str) -> Category:
    return Category(id=uuid4(), name=name, slug=name.lower())


def _product(sku: str, categories: list[Category], **overrides: object) -> Product:
    values: dict[str, object] = {
        "id": uuid4(),
        "name": f"Product {sku}",
        "slug": f"product-{sku.lower()}",
        "sku": sku,
        "price": PricePair(Decimal("399.00"), Decimal("599.00")),
        "status": ProductStatus.ACTIVE,
        "category_ids": [c.id for c in categories],
        "primary_category_id": categories[0].id if categories else None,
        "variants": [
            ProductVariant(id=uuid4(), sku=f"{sku}-S", size="S", stock_quantity=3),
            ProductVariant(
                id=uuid4(), sku=f"{sku}-L", size="L", selling_price_override=Decimal("449.00")
            ),
        ],
        **overrides,
    }
    return Product(**values)  # type: ignore[arg-type]


def test_product_aggregate_round_trip(container: Container) -> None:
    with container.session_factory() as session:
        categories = SqlAlchemyCategoryRepository(session)
        girls, party = _category("Girls"), _category("Party")
        categories.add(girls)
        categories.add(party)
        repo = SqlAlchemyProductRepository(session)
        product = _product("A", [girls, party])
        repo.add(product)
        session.commit()

    with container.session_factory() as session:
        repo = SqlAlchemyProductRepository(session)
        loaded = repo.get(product.id)
        assert loaded is not None
        assert loaded.price == PricePair(Decimal("399.00"), Decimal("599.00"))
        assert [v.sku for v in loaded.variants] == ["A-S", "A-L"]
        assert loaded.variants[1].selling_price_override == Decimal("449.00")
        assert set(loaded.category_ids) == {girls.id, party.id}
        assert loaded.primary_category_id == girls.id
        assert loaded.created_at is not None and loaded.created_at.tzinfo is not None

        # Edit: drop a variant, change price, remove a category.
        loaded.variants = loaded.variants[:1]
        loaded.price = PricePair(Decimal("349.00"), None)
        loaded.category_ids = [girls.id]
        repo.save(loaded)
        session.commit()

    with container.session_factory() as session:
        again = SqlAlchemyProductRepository(session).get(product.id)
        assert again is not None
        assert [v.sku for v in again.variants] == ["A-S"]
        assert again.price.original is None
        assert again.category_ids == [girls.id]


def test_new_category_membership_appends_to_that_categorys_order(container: Container) -> None:
    with container.session_factory() as session:
        cats = SqlAlchemyCategoryRepository(session)
        girls = _category("Girls")
        cats.add(girls)
        repo = SqlAlchemyProductRepository(session)
        first, second, third = (_product(s, [girls]) for s in ("A", "B", "C"))
        for p in (first, second, third):
            repo.add(p)
        cats.set_product_order(girls.id, [third.id, first.id])  # second keeps its place after
        session.commit()
        assert cats.product_ids(girls.id) == [third.id, first.id, second.id]

        # Re-saving a product must not reset its position in the category.
        loaded = repo.get(first.id)
        assert loaded is not None
        repo.save(loaded)
        session.commit()
        assert cats.product_ids(girls.id) == [third.id, first.id, second.id]


def test_collection_membership_is_replaced_atomically(container: Container) -> None:
    from app.domain.entities.content import Collection

    with container.session_factory() as session:
        repo = SqlAlchemyProductRepository(session)
        products = [_product(s, []) for s in ("A", "B", "C")]
        for p in products:
            repo.add(p)
        collections = SqlAlchemyCollectionRepository(session)
        collection = Collection(id=uuid4(), name="Edit", slug="edit")
        collections.add(collection)
        collections.set_products(collection.id, [products[2].id, products[0].id])
        collections.set_products(collection.id, [products[1].id, products[2].id])
        session.commit()
        assert collections.product_ids(collection.id) == [products[1].id, products[2].id]


def test_product_media_ordering_and_restrict_delete(container: Container) -> None:
    with container.session_factory() as session:
        media_repo = SqlAlchemyMediaAssetRepository(session)
        assets = []
        for i in range(2):
            asset = MediaAsset(
                id=uuid4(),
                purpose=MediaPurpose.PRODUCT_IMAGE,
                visibility=MediaVisibility.PUBLIC,
                bucket="media",
                object_key=f"product_image/{i}.png",
                content_type="image/png",
                size_bytes=10,
                width=1,
                height=1,
                sha256="0" * 64,
                created_at=datetime.now(UTC),
            )
            media_repo.add(asset)
            assets.append(asset)
        repo = SqlAlchemyProductRepository(session)
        product = _product(
            "M", [], media=[ProductMediaLink(assets[1].id), ProductMediaLink(assets[0].id)]
        )
        repo.add(product)
        session.commit()
        loaded = repo.get(product.id)
        assert loaded is not None
        assert [m.media_asset_id for m in loaded.media] == [assets[1].id, assets[0].id]
        assert media_repo.in_use(assets[0].id)

        # The database refuses to delete an image that a product still uses.
        with pytest.raises(IntegrityError):
            media_repo.delete(assets[0].id)
        session.rollback()


def test_database_constraints_back_up_the_domain(container: Container) -> None:
    with container.session_factory() as session:
        repo = SqlAlchemyProductRepository(session)
        product = _product("X", [])
        repo.add(product)
        session.commit()
        row = session.get(ProductModel, product.id)
        assert row is not None
        row.original_price = Decimal("100.00")  # below selling price: violates CHECK constraint
        with pytest.raises(ConflictError):
            SqlAlchemyUnitOfWork(session).commit()


def test_one_primary_category_per_product(container: Container) -> None:
    with container.session_factory() as session:
        cats = SqlAlchemyCategoryRepository(session)
        a, b = _category("A"), _category("B")
        cats.add(a)
        cats.add(b)
        product = _product("P", [a, b])
        SqlAlchemyProductRepository(session).add(product)
        session.commit()
        link = session.scalars(
            select(ProductCategoryModel).where(ProductCategoryModel.category_id == b.id)
        ).one()
        link.is_primary = True
        with pytest.raises(IntegrityError):
            session.flush()


def test_sessions_can_be_revoked(container: Container) -> None:
    user = create_user(container, Role.CUSTOMER)
    now = datetime.now(UTC)
    with container.session_factory() as session:
        repo = SqlAlchemySessionRepository(session)
        auth = AuthSession(uuid4(), user.id, "a" * 64, now, now + timedelta(days=1))
        repo.add(auth, ip="127.0.0.1", user_agent="pytest")
        session.commit()
        assert repo.get_by_token_hash("a" * 64) is not None
        repo.revoke_all_for_user(user.id, now)
        session.commit()
        stored = repo.get_by_token_hash("a" * 64)
        assert stored is not None and not stored.is_valid(now)
