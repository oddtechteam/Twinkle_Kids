"use client";

import { Plus, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";

import { Button } from "@/components/ui/Button";
import { adminApi } from "@/lib/admin/api";
import { useMutation, useResource } from "@/lib/admin/hooks";
import type { AdminProductDetail, AdminProductSummary, Section, SectionPayload, SectionType, SelectionMode } from "@/lib/admin/types";
import { Card, CheckList, SelectInput, TextArea, TextInput, Toggle, adminStyles as styles } from "./Kit";
import { MediaField } from "./Pickers";
import { ProductOrdering } from "./ProductOrdering";
import { ICON_OPTIONS, SECTION_META, THEME_OPTIONS, cleanSettings } from "./sectionMeta";

type Settings = Record<string, unknown>;
type Obj = Record<string, unknown>;

const str = (v: unknown) => (typeof v === "string" ? v : "");
const obj = (v: unknown): Obj => (v && typeof v === "object" && !Array.isArray(v) ? (v as Obj) : {});
const arr = (v: unknown): Obj[] => (Array.isArray(v) ? (v as Obj[]) : []);

function toSummary(p: AdminProductDetail): AdminProductSummary {
  return {
    id: p.id,
    name: p.name,
    slug: p.slug,
    price: p.price,
    from_price: p.price.selling_price,
    price_varies: false,
    in_stock: p.variants.some((v) => v.in_stock),
    primary_image: p.images[0] ?? null,
    badges: p.badges,
    status: p.status,
    published_at: p.published_at,
  };
}

// --- Small reusable editors --------------------------------------------------------------------

function CtaEditor({ label, value, onChange }: { label: string; value: unknown; onChange: (v: Obj | null) => void }) {
  const cta = obj(value);
  return (
    <div className={styles.grid2}>
      <TextInput label={`${label} — text`} hint="Leave empty for no button" value={str(cta.label)} onChange={(v) => onChange({ ...cta, label: v })} maxLength={40} />
      <TextInput label={`${label} — link`} placeholder="/shop or https://…" value={str(cta.href)} onChange={(v) => onChange({ ...cta, href: v })} maxLength={500} />
    </div>
  );
}

interface ItemField {
  key: string;
  label: string;
  kind?: "text" | "textarea" | "icon";
  maxLength: number;
}

function Repeater({
  label,
  items,
  fields,
  max,
  onChange,
  blank,
}: {
  label: string;
  items: Obj[];
  fields: ItemField[];
  max: number;
  onChange: (items: Obj[]) => void;
  blank: () => Obj;
}) {
  const update = (index: number, patch: Obj) => onChange(items.map((item, i) => (i === index ? { ...item, ...patch } : item)));
  return (
    <div className={styles.stack}>
      <span className={styles.label}>{label}</span>
      {items.map((item, index) => (
        <div key={index} className={styles.blockEditor}>
          <div className={styles.blockHeader}>
            <span>#{index + 1}</span>
            <button type="button" className={`${styles.iconButton} ${styles.dangerIcon}`} onClick={() => onChange(items.filter((_, i) => i !== index))} aria-label="Remove item">
              <Trash2 size={15} aria-hidden="true" />
            </button>
          </div>
          {fields.map((f) =>
            f.kind === "icon" ? (
              <SelectInput key={f.key} label={f.label} value={str(item[f.key]) || "sparkles"} onChange={(v) => update(index, { [f.key]: v })} options={ICON_OPTIONS} />
            ) : f.kind === "textarea" ? (
              <TextArea key={f.key} label={f.label} value={str(item[f.key])} onChange={(v) => update(index, { [f.key]: v })} maxLength={f.maxLength} rows={3} />
            ) : (
              <TextInput key={f.key} label={f.label} value={str(item[f.key])} onChange={(v) => update(index, { [f.key]: v })} maxLength={f.maxLength} />
            ),
          )}
        </div>
      ))}
      <div>
        <Button size="sm" variant="soft" iconStart={<Plus aria-hidden="true" />} onClick={() => onChange([...items, blank()])} disabled={items.length >= max}>
          Add item
        </Button>
      </div>
    </div>
  );
}

// --- Per-type settings -------------------------------------------------------------------------

function SettingsFields({ type, settings, set }: { type: SectionType; settings: Settings; set: (key: string, value: unknown) => void }) {
  const categories = useResource(() => (type === "category_grid" ? adminApi.categories() : Promise.resolve([])), `cats-${type}`);
  const collections = useResource(() => (type === "collection_showcase" ? adminApi.collections() : Promise.resolve([])), `cols-${type}`);
  const theme = <SelectInput label="Colour theme" value={str(settings.theme)} onChange={(v) => set("theme", v)} options={THEME_OPTIONS} />;
  const eyebrow = <TextInput label="Eyebrow (small text above the title)" value={str(settings.eyebrow)} onChange={(v) => set("eyebrow", v)} maxLength={40} />;

  switch (type) {
    case "hero_banner": {
      const headline = obj(settings.headline);
      return (
        <>
          {eyebrow}
          <div className={styles.grid3}>
            <TextInput label="Headline" required value={str(headline.lead)} onChange={(v) => set("headline", { ...headline, lead: v })} maxLength={60} />
            <TextInput label="Highlighted words" value={str(headline.highlight)} onChange={(v) => set("headline", { ...headline, highlight: v })} maxLength={40} />
            <TextInput label="Headline ending" value={str(headline.trail)} onChange={(v) => set("headline", { ...headline, trail: v })} maxLength={60} />
          </div>
          <TextArea label="Body text" value={str(settings.body)} onChange={(v) => set("body", v)} maxLength={300} rows={3} />
          <CtaEditor label="Primary button" value={settings.primary_cta} onChange={(v) => set("primary_cta", v)} />
          <CtaEditor label="Secondary button" value={settings.secondary_cta} onChange={(v) => set("secondary_cta", v)} />
          <div className={styles.grid2}>
            {theme}
            <SelectInput
              label="Layout"
              value={str(settings.layout)}
              onChange={(v) => set("layout", v)}
              options={[
                { value: "image-right", label: "Image on the right" },
                { value: "image-left", label: "Image on the left" },
              ]}
            />
          </div>
          <Repeater
            label="Reassurance points (max 4)"
            items={arr(settings.trust)}
            max={4}
            fields={[
              { key: "icon", label: "Icon", kind: "icon", maxLength: 20 },
              { key: "label", label: "Text", maxLength: 40 },
            ]}
            blank={() => ({ icon: "sparkles", label: "" })}
            onChange={(v) => set("trust", v)}
          />
        </>
      );
    }
    case "category_grid":
      return (
        <>
          {eyebrow}
          <CheckList
            label="Categories (none selected = all top-level categories)"
            options={(categories.data ?? []).map((c) => ({ value: c.id, label: c.name }))}
            selected={(settings.category_ids as string[] | undefined) ?? []}
            onChange={(v) => set("category_ids", v)}
          />
          <div className={styles.grid2}>
            <SelectInput
              label="Layout"
              value={str(settings.layout)}
              onChange={(v) => set("layout", v)}
              options={[
                { value: "bento", label: "Feature tiles" },
                { value: "grid", label: "Even grid" },
              ]}
            />
            <Toggle label="Show “View all” link" checked={settings.show_view_all !== false} onChange={(v) => set("show_view_all", v)} />
          </div>
        </>
      );
    case "product_carousel":
    case "product_grid":
      return (
        <>
          {eyebrow}
          <CtaEditor label="Button" value={settings.cta} onChange={(v) => set("cta", v)} />
          <div className={styles.grid2}>
            {theme}
            <SelectInput
              label="Columns on desktop"
              value={String(settings.columns_desktop ?? 4)}
              onChange={(v) => set("columns_desktop", Number(v))}
              options={[
                { value: "3", label: "3" },
                { value: "4", label: "4" },
              ]}
            />
          </div>
        </>
      );
    case "editorial_banner":
    case "promo_banner":
      return (
        <>
          {eyebrow}
          <TextArea label="Body text" value={str(settings.body)} onChange={(v) => set("body", v)} maxLength={400} rows={3} />
          <CtaEditor label="Button" value={settings.cta} onChange={(v) => set("cta", v)} />
          <div className={styles.grid2}>
            {theme}
            <SelectInput
              label="Image position"
              value={str(settings.image_position)}
              onChange={(v) => set("image_position", v)}
              options={[
                { value: "right", label: "Right" },
                { value: "left", label: "Left" },
              ]}
            />
          </div>
        </>
      );
    case "collection_showcase":
      return (
        <>
          {eyebrow}
          <CheckList
            label="Collections (max 6)"
            options={(collections.data ?? []).map((c) => ({ value: c.id, label: c.status === "published" ? c.name : `${c.name} (draft — hidden)` }))}
            selected={(settings.collection_ids as string[] | undefined) ?? []}
            onChange={(v) => set("collection_ids", v.slice(0, 6))}
          />
          <SelectInput
            label="Layout"
            value={str(settings.layout)}
            onChange={(v) => set("layout", v)}
            options={[
              { value: "tiles", label: "Tiles" },
              { value: "row", label: "Row" },
            ]}
          />
        </>
      );
    case "occasion_collection":
      return (
        <>
          {eyebrow}
          <TextArea label="Body text" value={str(settings.body)} onChange={(v) => set("body", v)} maxLength={300} rows={3} />
          <CtaEditor label="Button" value={settings.cta} onChange={(v) => set("cta", v)} />
          {theme}
        </>
      );
    case "trust_strip":
      return (
        <Repeater
          label="Points (max 6)"
          items={arr(settings.items)}
          max={6}
          fields={[
            { key: "icon", label: "Icon", kind: "icon", maxLength: 20 },
            { key: "title", label: "Title", maxLength: 40 },
            { key: "text", label: "Text", maxLength: 140 },
          ]}
          blank={() => ({ icon: "sparkles", title: "", text: "" })}
          onChange={(v) => set("items", v)}
        />
      );
    case "testimonials":
      return (
        <>
          <p className={styles.notice}>Only add real reviews from customers who agreed to be quoted. Never write or edit reviews yourself.</p>
          <Repeater
            label="Reviews (max 12)"
            items={arr(settings.items)}
            max={12}
            fields={[
              { key: "quote", label: "Review", kind: "textarea", maxLength: 400 },
              { key: "author", label: "Customer name", maxLength: 60 },
              { key: "context", label: "Context (e.g. city or product)", maxLength: 60 },
            ]}
            blank={() => ({ quote: "", author: "", context: "" })}
            onChange={(v) => set("items", v)}
          />
        </>
      );
    case "faq":
      return (
        <Repeater
          label="Questions (max 20)"
          items={arr(settings.items)}
          max={20}
          fields={[
            { key: "question", label: "Question", maxLength: 160 },
            { key: "answer", label: "Answer", kind: "textarea", maxLength: 1000 },
          ]}
          blank={() => ({ question: "", answer: "" })}
          onChange={(v) => set("items", v)}
        />
      );
    case "announcement":
      return (
        <>
          <TextInput label="Message" required value={str(settings.message)} onChange={(v) => set("message", v)} maxLength={140} />
          <CtaEditor label="Link" value={settings.link} onChange={(v) => set("link", v)} />
          {theme}
        </>
      );
    case "contact":
      return (
        <>
          <TextArea label="Body text" value={str(settings.body)} onChange={(v) => set("body", v)} maxLength={300} rows={3} />
          <p className={styles.hint}>Contact details come from Settings → Contact. Options without a configured detail are hidden automatically.</p>
          <div className={styles.grid3}>
            <Toggle label="Show WhatsApp" checked={settings.show_whatsapp !== false} onChange={(v) => set("show_whatsapp", v)} />
            <Toggle label="Show phone" checked={settings.show_phone !== false} onChange={(v) => set("show_phone", v)} />
            <Toggle label="Show email" checked={settings.show_email !== false} onChange={(v) => set("show_email", v)} />
          </div>
        </>
      );
    case "rich_text":
      return (
        <>
          <TextArea label="Text" hint="Plain text only; blank lines separate paragraphs." required value={str(settings.body)} onChange={(v) => set("body", v)} maxLength={5000} rows={8} />
          <SelectInput
            label="Alignment"
            value={str(settings.alignment)}
            onChange={(v) => set("alignment", v)}
            options={[
              { value: "center", label: "Centred" },
              { value: "left", label: "Left" },
            ]}
          />
        </>
      );
  }
}

// --- Editor ------------------------------------------------------------------------------------

interface EditorState extends Omit<SectionPayload, "product_limit"> {
  product_limit: string;
}

function initialState(type: SectionType, section?: Section): EditorState {
  const meta = SECTION_META[type];
  if (section) {
    return {
      section_type: section.section_type,
      title: section.title ?? "",
      subtitle: section.subtitle ?? "",
      settings: { ...meta.defaults(), ...section.settings },
      is_visible: section.is_visible,
      desktop_media_id: section.desktop_media_id,
      mobile_media_id: section.mobile_media_id,
      selection_mode: section.selection_mode,
      source_category_id: section.source_category_id,
      source_collection_id: section.source_collection_id,
      product_limit: String(section.product_limit),
    };
  }
  return {
    section_type: type,
    title: "",
    subtitle: "",
    settings: meta.defaults(),
    is_visible: true,
    desktop_media_id: null,
    mobile_media_id: null,
    selection_mode: meta.defaultMode,
    source_category_id: null,
    source_collection_id: null,
    product_limit: "8",
  };
}

export function SectionEditor({ type, section, onSaved }: { type: SectionType; section?: Section; onSaved?: () => void }) {
  const router = useRouter();
  const meta = SECTION_META[type];
  const [s, setS] = useState(() => initialState(type, section));
  const { run, pending } = useMutation();
  const categories = useResource(() => (meta.products ? adminApi.categories() : Promise.resolve([])), `sel-cats-${type}`);
  const collections = useResource(() => (meta.products ? adminApi.collections() : Promise.resolve([])), `sel-cols-${type}`);
  const manualProducts = useResource(
    () =>
      section && section.selection_mode === "manual"
        ? Promise.all(section.product_ids.map((id) => adminApi.product(id).then(toSummary)))
        : Promise.resolve([] as AdminProductSummary[]),
    `${section?.id ?? "new"}-${section?.selection_mode}-${section?.product_ids.join(",")}`,
  );

  const set = <K extends keyof EditorState>(key: K, value: EditorState[K]) => setS((prev) => ({ ...prev, [key]: value }));
  const setSetting = (key: string, value: unknown) => setS((prev) => ({ ...prev, settings: { ...prev.settings, [key]: value } }));

  const modeOptions: { value: SelectionMode; label: string }[] =
    type === "occasion_collection"
      ? [{ value: "collection", label: "From a collection" }]
      : [
          { value: "newest", label: "Newest products" },
          { value: "category", label: "From a category" },
          { value: "collection", label: "From a collection (uses the collection's order)" },
          { value: "manual", label: "Hand-picked products (your own order)" },
        ];

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const payload: SectionPayload = {
      ...s,
      title: s.title?.trim() || null,
      subtitle: s.subtitle?.trim() || null,
      settings: cleanSettings(s.settings),
      desktop_media_id: meta.media ? s.desktop_media_id : null,
      mobile_media_id: meta.media ? s.mobile_media_id : null,
      source_category_id: s.selection_mode === "category" ? s.source_category_id : null,
      source_collection_id: s.selection_mode === "collection" ? s.source_collection_id : null,
      product_limit: Math.min(48, Math.max(1, Number.parseInt(s.product_limit || "8", 10) || 8)),
    };
    if (section) {
      const res = await run(() => adminApi.updateSection(section.id, payload), { success: "Section saved to draft" });
      if (res.ok) onSaved?.();
    } else {
      const res = await run(() => adminApi.createSection(payload), { success: "Section added to draft" });
      if (res.ok) router.replace(`/admin/homepage/${res.result.id}`);
    }
  };

  return (
    <div className={styles.stack}>
      <form onSubmit={submit} className={styles.twoCol} noValidate>
        <div className={styles.stack}>
          <Card title="Content">
            <TextInput label="Title" value={s.title ?? ""} onChange={(v) => set("title", v)} maxLength={120} />
            <TextInput label="Subtitle" value={s.subtitle ?? ""} onChange={(v) => set("subtitle", v)} maxLength={255} />
            <SettingsFields type={type} settings={s.settings} set={setSetting} />
          </Card>

          {meta.media && (
            <Card title="Images" hint="The mobile image is optional; the desktop image is used when it is empty.">
              <div className={styles.grid2}>
                <MediaField label="Desktop image" value={s.desktop_media_id} onChange={(id) => set("desktop_media_id", id)} purpose="homepage_banner" />
                <MediaField label="Mobile image" value={s.mobile_media_id} onChange={(id) => set("mobile_media_id", id)} purpose="homepage_banner" />
              </div>
            </Card>
          )}

          {meta.products && (
            <Card title="Products">
              <SelectInput label="Which products" value={s.selection_mode} onChange={(v) => set("selection_mode", v as SelectionMode)} options={modeOptions} />
              {s.selection_mode === "category" && (
                <SelectInput
                  label="Category"
                  value={s.source_category_id ?? ""}
                  onChange={(v) => set("source_category_id", v || null)}
                  placeholder="Choose a category"
                  options={(categories.data ?? []).map((c) => ({ value: c.id, label: c.name }))}
                />
              )}
              {s.selection_mode === "collection" && (
                <SelectInput
                  label="Collection"
                  value={s.source_collection_id ?? ""}
                  onChange={(v) => set("source_collection_id", v || null)}
                  placeholder="Choose a collection"
                  options={(collections.data ?? []).map((c) => ({ value: c.id, label: c.status === "published" ? c.name : `${c.name} (draft)` }))}
                />
              )}
              <TextInput label="Maximum products shown" type="number" min={1} max={48} value={s.product_limit} onChange={(v) => set("product_limit", v)} />
              {s.selection_mode === "manual" && !(section && section.selection_mode === "manual") && (
                <p className={styles.hint}>Save the section first, then pick and order its products below.</p>
              )}
            </Card>
          )}
        </div>

        <div className={styles.stack}>
          <Card title="Draft">
            <Toggle label="Visible on the homepage" checked={s.is_visible} onChange={(v) => set("is_visible", v)} />
            <p className={styles.hint}>Saving updates the draft only. Publish from the homepage builder to make it live.</p>
            <Button type="submit" fullWidth loading={pending}>
              {section ? "Save section" : "Add section"}
            </Button>
          </Card>
        </div>
      </form>

      {section && section.selection_mode === "manual" && manualProducts.data && (
        <ProductOrdering
          key={`${section.id}-${section.product_ids.join(",")}`}
          title="Hand-picked products"
          hint="This order applies only to this homepage section. Only active, in-stock products are shown to customers."
          initial={manualProducts.data}
          onSave={async (ids) => {
            await adminApi.setSectionProducts(section.id, ids);
            onSaved?.();
          }}
        />
      )}
    </div>
  );
}
