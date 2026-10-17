"""Admin CMS: homepage builder, store settings, navigation, website pages, shipping rules,
size charts and the dashboard. Every route checks permissions server-side."""

from uuid import UUID

from fastapi import APIRouter, status

from app.api.deps import (
    CatalogManagerDep,
    ContentManagerDep,
    DashboardDep,
    HomepageBuilderDep,
    NavigationServiceDep,
    PageServiceDep,
    SettingsManagerDep,
    SettingsServiceDep,
    ShippingServiceDep,
    SizeChartServiceDep,
    StaffUserDep,
)
from app.api.schemas.admin import (
    CreatedOut,
    IdsIn,
    NavigationIn,
    OrderingIn,
    PageIn,
    PublishIn,
    SectionIn,
    SettingsPatch,
    ShippingRuleIn,
    SizeChartIn,
    VisibilityIn,
)
from app.api.schemas.content import (
    DashboardOut,
    HomepageAdminOut,
    NavigationItemOut,
    PageOut,
    PublicationOut,
    SectionOut,
    SettingsOut,
    ShippingRuleOut,
    SizeChartOut,
)
from app.domain.enums import NavigationMenu

router = APIRouter(prefix="/admin", tags=["admin: content"])


# --- Dashboard --------------------------------------------------------------------------------


@router.get("/dashboard", response_model=DashboardOut)
def admin_dashboard(_: StaffUserDep, dashboard: DashboardDep) -> DashboardOut:
    return DashboardOut.model_validate(dashboard.summary())


# --- Homepage builder -------------------------------------------------------------------------


@router.get("/homepage", response_model=HomepageAdminOut)
def homepage_overview(_: ContentManagerDep, builder: HomepageBuilderDep) -> HomepageAdminOut:
    """Draft sections (in order) and the live publication status."""
    return HomepageAdminOut(
        sections=[SectionOut.of(v) for v in builder.list()],
        publication=PublicationOut.of(builder.publication()),
    )


@router.post("/homepage/sections", response_model=CreatedOut, status_code=status.HTTP_201_CREATED)
def create_section(body: SectionIn, user: ContentManagerDep, builder: HomepageBuilderDep) -> CreatedOut:
    return CreatedOut(id=builder.create(body.to_input(), actor_id=user.id))


@router.put("/homepage/sections/order", status_code=status.HTTP_204_NO_CONTENT)
def reorder_sections(body: IdsIn, user: ContentManagerDep, builder: HomepageBuilderDep) -> None:
    builder.reorder(body.ids, actor_id=user.id)


@router.get("/homepage/sections/{section_id}", response_model=SectionOut)
def get_section(section_id: UUID, _: ContentManagerDep, builder: HomepageBuilderDep) -> SectionOut:
    return SectionOut.of(builder.get(section_id))


@router.put("/homepage/sections/{section_id}", status_code=status.HTTP_204_NO_CONTENT)
def update_section(
    section_id: UUID, body: SectionIn, user: ContentManagerDep, builder: HomepageBuilderDep
) -> None:
    builder.update(section_id, body.to_input(), actor_id=user.id)


@router.patch("/homepage/sections/{section_id}/visibility", status_code=status.HTTP_204_NO_CONTENT)
def set_section_visibility(
    section_id: UUID, body: VisibilityIn, user: ContentManagerDep, builder: HomepageBuilderDep
) -> None:
    builder.set_visibility(section_id, body.is_visible, actor_id=user.id)


@router.delete("/homepage/sections/{section_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_section(section_id: UUID, user: ContentManagerDep, builder: HomepageBuilderDep) -> None:
    builder.delete(section_id, actor_id=user.id)


@router.put("/homepage/sections/{section_id}/products", status_code=status.HTTP_204_NO_CONTENT)
def set_section_products(
    section_id: UUID, body: OrderingIn, user: ContentManagerDep, builder: HomepageBuilderDep
) -> None:
    """Hand-picked products for a manual section, in this section's own order."""
    builder.set_products(section_id, body.product_ids, actor_id=user.id)


@router.post("/homepage/publish", response_model=PublicationOut)
def publish_homepage(body: PublishIn, user: ContentManagerDep, builder: HomepageBuilderDep) -> PublicationOut:
    builder.publish(actor_id=user.id, note=body.note)
    return PublicationOut.of(builder.publication())


# --- Store settings ---------------------------------------------------------------------------


@router.get("/settings", response_model=SettingsOut)
def get_settings(_: SettingsManagerDep, service: SettingsServiceDep) -> SettingsOut:
    return SettingsOut.of(service.get())


@router.patch("/settings", response_model=SettingsOut)
def update_settings(body: SettingsPatch, user: SettingsManagerDep, service: SettingsServiceDep) -> SettingsOut:
    return SettingsOut.of(service.update(body.changes(), actor_id=user.id))


# --- Navigation -------------------------------------------------------------------------------


@router.get("/navigation", response_model=list[NavigationItemOut])
def list_navigation(
    _: ContentManagerDep, service: NavigationServiceDep, menu: NavigationMenu | None = None
) -> list[NavigationItemOut]:
    return [NavigationItemOut.model_validate(i) for i in service.list(menu)]


@router.post("/navigation", response_model=CreatedOut, status_code=status.HTTP_201_CREATED)
def create_navigation_item(
    body: NavigationIn, user: ContentManagerDep, service: NavigationServiceDep
) -> CreatedOut:
    return CreatedOut(id=service.create(body.to_input(), actor_id=user.id))


@router.put("/navigation/order", status_code=status.HTTP_204_NO_CONTENT)
def reorder_navigation(body: IdsIn, user: ContentManagerDep, service: NavigationServiceDep) -> None:
    service.reorder(body.ids, actor_id=user.id)


@router.put("/navigation/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def update_navigation_item(
    item_id: UUID, body: NavigationIn, user: ContentManagerDep, service: NavigationServiceDep
) -> None:
    service.update(item_id, body.to_input(), actor_id=user.id)


@router.delete("/navigation/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_navigation_item(item_id: UUID, user: ContentManagerDep, service: NavigationServiceDep) -> None:
    service.delete(item_id, actor_id=user.id)


# --- Website pages ----------------------------------------------------------------------------


@router.get("/pages", response_model=list[PageOut])
def list_pages(_: ContentManagerDep, service: PageServiceDep) -> list[PageOut]:
    return [PageOut.model_validate(p) for p in service.list()]


@router.post("/pages", response_model=CreatedOut, status_code=status.HTTP_201_CREATED)
def create_page(body: PageIn, user: ContentManagerDep, service: PageServiceDep) -> CreatedOut:
    return CreatedOut(id=service.create(body.to_input(), actor_id=user.id))


@router.get("/pages/{page_id}", response_model=PageOut)
def get_page(page_id: UUID, _: ContentManagerDep, service: PageServiceDep) -> PageOut:
    return PageOut.model_validate(service.get(page_id))


@router.put("/pages/{page_id}", status_code=status.HTTP_204_NO_CONTENT)
def update_page(page_id: UUID, body: PageIn, user: ContentManagerDep, service: PageServiceDep) -> None:
    service.update(page_id, body.to_input(), actor_id=user.id)


@router.delete("/pages/{page_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_page(page_id: UUID, user: ContentManagerDep, service: PageServiceDep) -> None:
    service.delete(page_id, actor_id=user.id)


# --- Shipping rules ---------------------------------------------------------------------------


@router.get("/shipping-rules", response_model=list[ShippingRuleOut])
def list_shipping_rules(_: SettingsManagerDep, service: ShippingServiceDep) -> list[ShippingRuleOut]:
    return [ShippingRuleOut.model_validate(r) for r in service.list()]


@router.post("/shipping-rules", response_model=CreatedOut, status_code=status.HTTP_201_CREATED)
def create_shipping_rule(
    body: ShippingRuleIn, user: SettingsManagerDep, service: ShippingServiceDep
) -> CreatedOut:
    return CreatedOut(id=service.create(body.to_input(), actor_id=user.id))


@router.put("/shipping-rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def update_shipping_rule(
    rule_id: UUID, body: ShippingRuleIn, user: SettingsManagerDep, service: ShippingServiceDep
) -> None:
    service.update(rule_id, body.to_input(), actor_id=user.id)


@router.delete("/shipping-rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_shipping_rule(rule_id: UUID, user: SettingsManagerDep, service: ShippingServiceDep) -> None:
    service.delete(rule_id, actor_id=user.id)


# --- Size charts ------------------------------------------------------------------------------


@router.get("/size-charts", response_model=list[SizeChartOut])
def list_size_charts(_: CatalogManagerDep, service: SizeChartServiceDep) -> list[SizeChartOut]:
    return [SizeChartOut.model_validate(c) for c in service.list()]


@router.post("/size-charts", response_model=CreatedOut, status_code=status.HTTP_201_CREATED)
def create_size_chart(
    body: SizeChartIn, user: CatalogManagerDep, service: SizeChartServiceDep
) -> CreatedOut:
    return CreatedOut(id=service.create(body.to_input(), actor_id=user.id))


@router.put("/size-charts/{chart_id}", status_code=status.HTTP_204_NO_CONTENT)
def update_size_chart(
    chart_id: UUID, body: SizeChartIn, user: CatalogManagerDep, service: SizeChartServiceDep
) -> None:
    service.update(chart_id, body.to_input(), actor_id=user.id)


@router.delete("/size-charts/{chart_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_size_chart(chart_id: UUID, user: CatalogManagerDep, service: SizeChartServiceDep) -> None:
    service.delete(chart_id, actor_id=user.id)

