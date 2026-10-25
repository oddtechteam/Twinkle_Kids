"""Public, unauthenticated content for the storefront. Published content only."""

from fastapi import APIRouter

from app.api.deps import (
    CatalogReaderDep,
    PageServiceDep,
    PublicHomepageDep,
    PublicSiteDep,
    ShippingServiceDep,
)
from app.api.schemas.content import (
    CollectionOut,
    PublicPageOut,
    PublicSiteOut,
    PublicShippingRuleOut,
    PublishedHomepageOut,
)

router = APIRouter(tags=["content"])


@router.get("/content/site", response_model=PublicSiteOut)
def site(reader: PublicSiteDep) -> PublicSiteOut:
    """Store name, branding, theme, announcement, contact details and resolved menus."""
    return PublicSiteOut.of(reader.get())


@router.get("/content/homepage", response_model=PublishedHomepageOut)
def homepage(reader: PublicHomepageDep) -> PublishedHomepageOut:
    """The latest *published* homepage snapshot, resolved against live catalogue data.
    Draft edits are never visible here."""
    return PublishedHomepageOut.model_validate(reader.get())


@router.get("/content/pages/{slug}", response_model=PublicPageOut)
def page(slug: str, service: PageServiceDep) -> PublicPageOut:
    return PublicPageOut.model_validate(service.published(slug))


@router.get("/content/shipping", response_model=list[PublicShippingRuleOut])
def shipping(service: ShippingServiceDep) -> list[PublicShippingRuleOut]:
    """Active shipping fee bands, so product pages can show delivery charges from settings."""
    return [PublicShippingRuleOut.model_validate(r) for r in service.list() if r.is_active]


@router.get("/collections", response_model=list[CollectionOut])
def collections(reader: CatalogReaderDep) -> list[CollectionOut]:
    """Published collections in display order."""
    return [CollectionOut.model_validate(c) for c in reader.collections()]


@router.get("/collections/{slug}", response_model=CollectionOut)
def collection(slug: str, reader: CatalogReaderDep) -> CollectionOut:
    """Published collection details (products: GET /products?collection=<slug>)."""
    return CollectionOut.model_validate(reader.collection(slug))
