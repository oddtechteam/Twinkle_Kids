"use client";

import { Crop, ImagePlus, Plus, Trash2, Wand2 } from "lucide-react";
import { type FormEvent, useMemo, useState } from "react";

import { Button } from "@/components/ui/Button";
import { adminApi } from "@/lib/admin/api";
import { useResource } from "@/lib/admin/hooks";
import type { AdminProductDetail, MediaAsset, ProductPayload, ProductStatus } from "@/lib/admin/types";
import { formatMoney } from "@/lib/format";
import {
  Card,
  CheckList,
  MoneyInput,
  SelectInput,
  SortableList,
  TagInput,
  TextArea,
  TextInput,
  Toggle,
  adminStyles as styles,
} from "./Kit";
import { ImageCropDialog } from "./ImageCropper";
import { MediaPicker, MediaThumb, ProductPicker } from "./Pickers";

interface VariantRow {
  key: string;
  id: string | null;
  sku: string;
  size: string;
  colour: string;
  colour_hex: string;
  selling_price: string;
  original_price: string;
  stock_quantity: string;
  is_active: boolean;
}

interface MediaRow {
  media_asset_id: string;
  url: string;
  /** The saved 4:5 product crop, shown as the thumbnail when there is one. */
  crop_url?: string | null;
  alt_text: string;
  variant_sku: string;
}

export interface ProductFormState {
  name: string;
  slug: string;
  sku: string;
  selling_price: string;
  original_price: string;
  status: ProductStatus;
  short_description: string;
  description: string;
  track_inventory: boolean;
  allow_backorder: boolean;
  low_stock_threshold: string;
  size_chart_id: string;
  seo_title: string;
  seo_description: string;
  category_ids: string[];
  primary_category_id: string;
  collection_ids: string[];
  badges: string[];
  is_featured: boolean;
  related: { id: string; name: string }[];
  variants: VariantRow[];
  media: MediaRow[];
}

let keySeq = 0;
const newKey = () => `v${++keySeq}`;

export function emptyProduct(): ProductFormState {
  return {
    name: "",
    slug: "",
    sku: "",
    selling_price: "",
    original_price: "",
    status: "draft",
    short_description: "",
    description: "",
    track_inventory: true,
    allow_backorder: false,
    low_stock_threshold: "3",
    size_chart_id: "",
    seo_title: "",
    seo_description: "",
    category_ids: [],
    primary_category_id: "",
    collection_ids: [],
    badges: [],
    is_featured: false,
    related: [],
    variants: [],
    media: [],
  };
}

export function fromDetail(p: AdminProductDetail): ProductFormState {
  const skuById = new Map(p.variants.map((v) => [v.id, v.sku]));
  return {
    name: p.name,
    slug: p.slug,
    sku: p.sku,
    selling_price: p.price.selling_price,
    original_price: p.price.original_price ?? "",
    status: p.status,
    short_description: p.short_description ?? "",
    description: p.description ?? "",
    track_inventory: p.track_inventory,
    allow_backorder: p.allow_backorder,
    low_stock_threshold: String(p.low_stock_threshold),
    size_chart_id: p.size_chart_id ?? "",
    seo_title: p.seo_title ?? "",
    seo_description: p.seo_description ?? "",
    category_ids: p.categories.map((c) => c.id),
    primary_category_id: p.primary_category_id ?? "",
    collection_ids: p.collection_ids,
    badges: p.badges,
    is_featured: p.is_featured ?? false,
    related: (p.related_product_ids ?? []).map((id) => ({ id, name: "" })),
    variants: p.variants.map((v) => ({
      key: newKey(),
      id: v.id,
      sku: v.sku,
      size: v.size ?? "",
      colour: v.colour ?? "",
      colour_hex: v.colour_hex ?? "",
      selling_price: v.selling_price_override ?? "",
      original_price: v.original_price_override ?? "",
      stock_quantity: String(v.stock_quantity ?? 0),
      is_active: v.is_active,
    })),
    media: p.images.map((img) => ({
      media_asset_id: img.media_asset_id,
      url: img.url,
      crop_url: img.crops?.product?.url ?? null,
      alt_text: img.alt_text ?? "",
      variant_sku: (img.variant_id && skuById.get(img.variant_id)) || "",
    })),
  };
}

const orNull = (value: string) => (value.trim() === "" ? null : value.trim());

export function toPayload(f: ProductFormState): ProductPayload {
  return {
    name: f.name.trim(),
    slug: orNull(f.slug),
    sku: f.sku.trim(),
    selling_price: f.selling_price,
    original_price: orNull(f.original_price),
    status: f.status,
    short_description: orNull(f.short_description),
    description: orNull(f.description),
    track_inventory: f.track_inventory,
    allow_backorder: f.allow_backorder,
    low_stock_threshold: Number.parseInt(f.low_stock_threshold || "0", 10),
    size_chart_id: orNull(f.size_chart_id),
    seo_title: orNull(f.seo_title),
    seo_description: orNull(f.seo_description),
    category_ids: f.category_ids,
    primary_category_id: orNull(f.primary_category_id),
    collection_ids: f.collection_ids,
    badges: f.badges,
    is_featured: f.is_featured,
    related_product_ids: f.related.map((r) => r.id),
    variants: f.variants.map((v) => ({
      id: v.id,
      sku: v.sku.trim(),
      size: orNull(v.size),
      colour: orNull(v.colour),
      colour_hex: orNull(v.colour_hex),
      selling_price: orNull(v.selling_price),
      original_price: orNull(v.original_price),
      stock_quantity: Number.parseInt(v.stock_quantity || "0", 10),
      is_active: v.is_active,
    })),
    media: f.media.map((m) => ({
      media_asset_id: m.media_asset_id,
      alt_text: orNull(m.alt_text),
      variant_sku: orNull(m.variant_sku),
    })),
  };
}

/** Client-side checks for obvious mistakes; the backend re-validates everything. */
function problems(f: ProductFormState): string[] {
  const out: string[] = [];
  const money = /^\d{1,10}(\.\d{1,2})?$/;
  if (!f.name.trim()) out.push("Product name is required.");
  if (!f.sku.trim()) out.push("Product SKU is required.");
  if (!money.test(f.selling_price)) out.push("Selling price is required (e.g. 399 or 399.00).");
  if (f.original_price && !money.test(f.original_price)) out.push("Original price/MRP must be a valid amount.");
  if (f.original_price && money.test(f.selling_price) && Number(f.original_price) < Number(f.selling_price)) {
    out.push("Original price/MRP must be greater than or equal to the selling price.");
  }
  if (f.variants.length === 0) out.push("Add at least one variant (size/colour option with its SKU and stock).");
  if (f.variants.some((v) => !v.sku.trim())) out.push("Every variant needs a SKU.");
  return out;
}

export function ProductForm({
  initial,
  saved,
  submitLabel,
  onSubmit,
  pending,
}: {
  initial: ProductFormState;
  /** Last saved product (for server-calculated discount display). */
  saved?: AdminProductDetail;
  submitLabel: string;
  onSubmit: (payload: ProductPayload) => void;
  pending: boolean;
}) {
  const [f, setF] = useState(initial);
  const [touched, setTouched] = useState(false);
  const [picking, setPicking] = useState(false);
  const [cropping, setCropping] = useState<MediaAsset | null>(null);
  const [genSizes, setGenSizes] = useState<string[]>([]);
  const [genColours, setGenColours] = useState<string[]>([]);
  const categories = useResource(adminApi.categories, "categories");
  const collections = useResource(() => adminApi.collections().catch(() => []), "collections");
  const charts = useResource(() => adminApi.sizeCharts().catch(() => []), "size-charts");
  const issues = useMemo(() => problems(f), [f]);

  const set = <K extends keyof ProductFormState>(key: K, value: ProductFormState[K]) => setF((s) => ({ ...s, [key]: value }));
  const setVariant = (key: string, patch: Partial<VariantRow>) =>
    setF((s) => ({ ...s, variants: s.variants.map((v) => (v.key === key ? { ...v, ...patch } : v)) }));

  const addVariant = () =>
    setF((s) => ({
      ...s,
      variants: [
        ...s.variants,
        {
          key: newKey(),
          id: null,
          sku: s.sku ? `${s.sku}-${s.variants.length + 1}` : "",
          size: "",
          colour: "",
          colour_hex: "",
          selling_price: "",
          original_price: "",
          stock_quantity: "0",
          is_active: true,
        },
      ],
    }));

  const generate = () => {
    const sizes = genSizes.length ? genSizes : [""];
    const colours = genColours.length ? genColours : [""];
    setF((s) => {
      const existing = new Set(s.variants.map((v) => `${v.size.toLowerCase()}|${v.colour.toLowerCase()}`));
      const added: VariantRow[] = [];
      for (const colour of colours) {
        for (const size of sizes) {
          if (existing.has(`${size.toLowerCase()}|${colour.toLowerCase()}`)) continue;
          const parts = [s.sku || "SKU", colour.slice(0, 3).toUpperCase(), size.replace(/[^a-zA-Z0-9]/g, "").toUpperCase()].filter(Boolean);
          added.push({
            key: newKey(),
            id: null,
            sku: parts.join("-"),
            size,
            colour,
            colour_hex: "",
            selling_price: "",
            original_price: "",
            stock_quantity: "0",
            is_active: true,
          });
        }
      }
      return { ...s, variants: [...s.variants, ...added] };
    });
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    setTouched(true);
    if (issues.length === 0) onSubmit(toPayload(f));
  };

  const categoryOptions = (categories.data ?? []).map((c) => ({ value: c.id, label: c.is_active ? c.name : `${c.name} (hidden)` }));

  return (
    <form onSubmit={submit} className={styles.twoCol} noValidate>
      <div className={styles.stack}>
        <Card title="Details">
          <TextInput label="Product name" value={f.name} onChange={(v) => set("name", v)} required maxLength={200} />
          <div className={styles.grid2}>
            <TextInput label="Slug" hint="Leave empty to generate from the name" value={f.slug} onChange={(v) => set("slug", v)} maxLength={160} />
            <TextInput label="Product SKU" value={f.sku} onChange={(v) => set("sku", v.toUpperCase())} required maxLength={64} />
          </div>
          <TextArea label="Short description" value={f.short_description} onChange={(v) => set("short_description", v)} rows={2} maxLength={500} />
          <TextArea label="Description" hint="Plain text; blank lines separate paragraphs." value={f.description} onChange={(v) => set("description", v)} rows={6} maxLength={20000} />
        </Card>

        <Card title="Pricing" hint="Both prices are stored separately. Customers see a discount only when the MRP is higher than the selling price.">
          <div className={styles.grid2}>
            <MoneyInput label="Selling price" value={f.selling_price} onChange={(v) => set("selling_price", v)} required placeholder="399.00" />
            <MoneyInput label="Original price / MRP" hint="Optional" value={f.original_price} onChange={(v) => set("original_price", v)} placeholder="599.00" />
          </div>
          {saved && (
            <p className={styles.hint}>
              Saved: {formatMoney(saved.price.selling_price)}
              {saved.price.original_price && <> · MRP {formatMoney(saved.price.original_price)}</>}
              {saved.price.discount_percent !== null && <> · {saved.price.discount_percent}% off (calculated by the store)</>}
            </p>
          )}
        </Card>

        <Card
          title="Variants & inventory"
          hint="Sizes and colours are specific to this product. Leave variant prices empty to inherit the product prices."
          actions={
            <Button size="sm" variant="soft" iconStart={<Plus aria-hidden="true" />} onClick={addVariant}>
              Add variant
            </Button>
          }
        >
          <div className={styles.grid2}>
            <TagInput label="Generate sizes" hint="e.g. 2-3Y, 3-4Y" values={genSizes} onChange={setGenSizes} maxLength={40} />
            <TagInput label="Generate colours" hint="e.g. Blush, Navy" values={genColours} onChange={setGenColours} maxLength={40} />
          </div>
          <div>
            <Button size="sm" variant="outline" iconStart={<Wand2 aria-hidden="true" />} onClick={generate} disabled={!genSizes.length && !genColours.length}>
              Create missing combinations
            </Button>
          </div>
          <div className={styles.grid2}>
            <Toggle label="Track inventory" checked={f.track_inventory} onChange={(v) => set("track_inventory", v)} />
            <Toggle label="Allow backorders" checked={f.allow_backorder} onChange={(v) => set("allow_backorder", v)} />
          </div>
          <TextInput label="Low-stock threshold" type="number" min={0} value={f.low_stock_threshold} onChange={(v) => set("low_stock_threshold", v)} />
          {f.variants.length === 0 && <p className={styles.hint}>No variants yet.</p>}
          {f.variants.map((v) => (
            <div key={v.key} className={styles.blockEditor}>
              <div className={styles.blockHeader}>
                <span>{[v.size, v.colour].filter(Boolean).join(" / ") || "Variant"}</span>
                <span style={{ display: "flex", gap: "var(--space-2)", alignItems: "center" }}>
                  <Toggle label="Active" checked={v.is_active} onChange={(val) => setVariant(v.key, { is_active: val })} />
                  <button
                    type="button"
                    className={`${styles.iconButton} ${styles.dangerIcon}`}
                    onClick={() => setF((s) => ({ ...s, variants: s.variants.filter((x) => x.key !== v.key) }))}
                    aria-label="Remove variant"
                  >
                    <Trash2 size={15} aria-hidden="true" />
                  </button>
                </span>
              </div>
              <div className={styles.grid3}>
                <TextInput label="SKU" value={v.sku} onChange={(val) => setVariant(v.key, { sku: val.toUpperCase() })} maxLength={64} />
                <TextInput label="Size" value={v.size} onChange={(val) => setVariant(v.key, { size: val })} maxLength={40} />
                <TextInput label="Colour" value={v.colour} onChange={(val) => setVariant(v.key, { colour: val })} maxLength={40} />
                <TextInput label="Colour swatch (hex)" placeholder="#F5CDD3" value={v.colour_hex} onChange={(val) => setVariant(v.key, { colour_hex: val })} maxLength={7} />
                <MoneyInput label="Selling price override" value={v.selling_price} onChange={(val) => setVariant(v.key, { selling_price: val })} placeholder="inherit" />
                <MoneyInput label="MRP override" value={v.original_price} onChange={(val) => setVariant(v.key, { original_price: val })} placeholder="inherit" />
                {v.id ? (
                  // Live stock changes only through Inventory (atomic, ledgered), never by overwriting it here.
                  <TextInput label="Stock (adjust in Inventory)" value={v.stock_quantity} onChange={() => undefined} readOnly disabled />
                ) : (
                  <TextInput label="Opening stock" type="number" min={0} value={v.stock_quantity} onChange={(val) => setVariant(v.key, { stock_quantity: val })} />
                )}
              </div>
            </div>
          ))}
        </Card>

        <Card
          title="Images"
          hint="Drag to reorder; the first image is the main product image. Crop each photo to the 4:5 product frame so every card lines up."
          actions={
            <Button size="sm" variant="soft" iconStart={<ImagePlus aria-hidden="true" />} onClick={() => setPicking(true)}>
              Add image
            </Button>
          }
        >
          {f.media.length === 0 ? (
            <p className={styles.hint}>No images yet — products without photos show an illustration.</p>
          ) : (
            <SortableList
              label="Product images"
              items={f.media}
              getId={(m) => m.media_asset_id}
              onReorder={(media) => set("media", media)}
              renderItem={(m) => (
                <div className={styles.grid2} style={{ alignItems: "center" }}>
                  <span className={styles.cellTitle}>
                    <span className={styles.thumb}>
                      <MediaThumb url={m.crop_url ?? m.url} alt={m.alt_text} />
                    </span>
                    <input
                      className={styles.input}
                      placeholder="Alt text (describe the image)"
                      value={m.alt_text}
                      maxLength={300}
                      aria-label="Alt text"
                      onChange={(e) =>
                        set("media", f.media.map((x) => (x.media_asset_id === m.media_asset_id ? { ...x, alt_text: e.target.value } : x)))
                      }
                    />
                  </span>
                  <select
                    className={styles.select}
                    aria-label="Show for variant"
                    value={m.variant_sku}
                    onChange={(e) =>
                      set("media", f.media.map((x) => (x.media_asset_id === m.media_asset_id ? { ...x, variant_sku: e.target.value } : x)))
                    }
                  >
                    <option value="">All variants</option>
                    {f.variants.filter((v) => v.sku).map((v) => (
                      <option key={v.key} value={v.sku}>
                        {v.sku}
                      </option>
                    ))}
                  </select>
                </div>
              )}
              renderActions={(m) => (
                <>
                  <button
                    type="button"
                    className={styles.iconButton}
                    onClick={() => adminApi.mediaAsset(m.media_asset_id).then(setCropping).catch(() => undefined)}
                    aria-label={m.crop_url ? "Edit crop" : "Crop image"}
                    title={m.crop_url ? "Edit crop" : "Crop to the product frame"}
                  >
                    <Crop size={15} aria-hidden="true" />
                  </button>
                  <button
                    type="button"
                    className={`${styles.iconButton} ${styles.dangerIcon}`}
                    onClick={() => set("media", f.media.filter((x) => x.media_asset_id !== m.media_asset_id))}
                    aria-label="Remove image from product"
                  >
                    <Trash2 size={15} aria-hidden="true" />
                  </button>
                </>
              )}
            />
          )}
          <MediaPicker
            open={picking}
            onClose={() => setPicking(false)}
            purpose="product_image"
            onSelect={(asset) => {
              if (f.media.some((m) => m.media_asset_id === asset.id)) return;
              const crop_url = asset.crops?.product?.url ?? null;
              set("media", [...f.media, { media_asset_id: asset.id, url: asset.url, crop_url, alt_text: asset.alt_text ?? "", variant_sku: "" }]);
              if (!crop_url && asset.visibility === "public") setCropping(asset); // frame new photos right away
            }}
          />
          {cropping && (
            <ImageCropDialog
              open
              asset={cropping}
              frame="product"
              onClose={() => setCropping(null)}
              onSaved={(asset) =>
                setF((state) => ({
                  ...state,
                  media: state.media.map((x) => (x.media_asset_id === asset.id ? { ...x, crop_url: asset.crops?.product?.url ?? null } : x)),
                }))
              }
            />
          )}
        </Card>

        <Card title="Search engine listing">
          <TextInput label="SEO title" value={f.seo_title} onChange={(v) => set("seo_title", v)} maxLength={70} hint={`${f.seo_title.length}/70`} />
          <TextArea label="SEO description" value={f.seo_description} onChange={(v) => set("seo_description", v)} maxLength={320} rows={3} hint={`${f.seo_description.length}/320`} />
        </Card>
      </div>

      <div className={styles.stack}>
        <Card title="Status">
          <SelectInput
            label="Visibility"
            value={f.status}
            onChange={(v) => set("status", v as ProductStatus)}
            options={[
              { value: "draft", label: "Draft (hidden)" },
              { value: "active", label: "Active (on the storefront)" },
              { value: "archived", label: "Archived" },
            ]}
          />
          {touched && issues.length > 0 && (
            <ul className={styles.notice} role="alert" style={{ paddingLeft: "var(--space-7)" }}>
              {issues.map((i) => (
                <li key={i}>{i}</li>
              ))}
            </ul>
          )}
          <Button type="submit" fullWidth loading={pending}>
            {submitLabel}
          </Button>
        </Card>

        <Card title="Organisation">
          <CheckList
            label="Categories"
            options={categoryOptions}
            selected={f.category_ids}
            onChange={(ids) => setF((s) => ({ ...s, category_ids: ids, primary_category_id: ids.includes(s.primary_category_id) ? s.primary_category_id : (ids[0] ?? "") }))}
          />
          {f.category_ids.length > 1 && (
            <SelectInput
              label="Primary category"
              value={f.primary_category_id}
              onChange={(v) => set("primary_category_id", v)}
              options={categoryOptions.filter((o) => f.category_ids.includes(o.value))}
            />
          )}
          <CheckList
            label="Collections"
            options={(collections.data ?? []).map((c) => ({ value: c.id, label: c.status === "published" ? c.name : `${c.name} (draft)` }))}
            selected={f.collection_ids}
            onChange={(ids) => set("collection_ids", ids)}
          />
          <SelectInput
            label="Size chart"
            value={f.size_chart_id}
            onChange={(v) => set("size_chart_id", v)}
            placeholder="No size chart"
            options={(charts.data ?? []).map((c) => ({ value: c.id, label: c.name }))}
          />
          <TagInput label="Badges" hint="Up to 3 short labels, e.g. “New season”" values={f.badges} onChange={(v) => set("badges", v)} max={3} />
          <Toggle label="Featured product" checked={f.is_featured} onChange={(v) => set("is_featured", v)} />
          <p className={styles.hint}>Featured products appear in “Featured” homepage sections.</p>
        </Card>
        <RelatedProducts value={f.related} selfId={saved?.id ?? null} onChange={(v) => set("related", v)} />
      </div>
    </form>
  );
}

/** Admin-curated "You may also like" products for this product (shown before bestsellers). */
function RelatedProducts({
  value,
  selfId,
  onChange,
}: {
  value: { id: string; name: string }[];
  selfId: string | null;
  onChange: (next: { id: string; name: string }[]) => void;
}) {
  const [picking, setPicking] = useState(false);
  const names = useResource(
    () => Promise.all(value.filter((r) => !r.name).map((r) => adminApi.product(r.id).then((p) => [p.id, p.name] as const))),
    value.map((r) => r.id).join(","),
  );
  const label = (r: { id: string; name: string }) => r.name || names.data?.find(([id]) => id === r.id)?.[1] || "Loading…";
  return (
    <Card title="Related products" hint="Shown as “You may also like” on this product's page. Up to 12, in this order.">
      {value.length === 0 ? (
        <p className={styles.hint}>None yet — bestsellers from the same category are shown instead (when there is order data).</p>
      ) : (
        <ol className={styles.list}>
          {value.map((r, index) => (
            <li key={r.id} className={styles.listRow}>
              <span>
                {index + 1}. {label(r)}
              </span>
              <Button size="sm" variant="ghost" iconStart={<Trash2 aria-hidden="true" size={14} />} onClick={() => onChange(value.filter((x) => x.id !== r.id))} aria-label={`Remove ${label(r)}`}>
                Remove
              </Button>
            </li>
          ))}
        </ol>
      )}
      <Button size="sm" variant="outline" iconStart={<Plus aria-hidden="true" size={14} />} disabled={value.length >= 12} onClick={() => setPicking(true)}>
        Add related products
      </Button>
      <ProductPicker
        open={picking}
        onClose={() => setPicking(false)}
        excludeIds={[...value.map((r) => r.id), ...(selfId ? [selfId] : [])]}
        onAdd={(products) => onChange([...value, ...products.map((p) => ({ id: p.id, name: p.name }))].slice(0, 12))}
      />
    </Card>
  );
}
