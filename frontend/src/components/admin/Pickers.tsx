"use client";

import Image from "next/image";
import { ImagePlus, Search, Upload, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { adminApi } from "@/lib/admin/api";
import { useMutation, useResource } from "@/lib/admin/hooks";
import type { AdminProductSummary, MediaAsset } from "@/lib/admin/types";
import { isRenderableImage } from "@/lib/catalog/adapters";
import { formatMoney } from "@/lib/format";
import { ErrorState, adminStyles as styles } from "./Kit";

export const MEDIA_PURPOSES = [
  { value: "product_image", label: "Product image" },
  { value: "category_image", label: "Category image" },
  { value: "collection_image", label: "Collection image" },
  { value: "homepage_banner", label: "Homepage banner" },
  { value: "content_image", label: "Content image" },
];

export function MediaThumb({ url, alt }: { url: string | null | undefined; alt?: string }) {
  if (!url || !isRenderableImage(url)) return null;
  return <Image src={url} alt={alt ?? ""} fill sizes="160px" />;
}

/** Browse the media library (and upload new files) to pick one asset. */
export function MediaPicker({
  open,
  onClose,
  onSelect,
  purpose,
}: {
  open: boolean;
  onClose: () => void;
  onSelect: (asset: MediaAsset) => void;
  purpose: string;
}) {
  const [filter, setFilter] = useState<string>(purpose);
  const media = useResource(() => adminApi.media({ purpose: filter || undefined, limit: 96 }), `${open}-${filter}`);
  const { run, pending } = useMutation();
  const input = useRef<HTMLInputElement>(null);

  const upload = async (file: File) => {
    const res = await run(() => adminApi.uploadMedia(file, purpose), { success: "Image uploaded" });
    if (res.ok) {
      onSelect(res.result);
      onClose();
    }
  };

  return (
    <Dialog open={open} onClose={onClose} title="Choose an image">
      <div className={styles.stack}>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)", alignItems: "center" }}>
          <select className={styles.select} style={{ width: "auto" }} value={filter} onChange={(e) => setFilter(e.target.value)}>
            <option value="">All images</option>
            {MEDIA_PURPOSES.map((p) => (
              <option key={p.value} value={p.value}>
                {p.label}
              </option>
            ))}
          </select>
          <input
            ref={input}
            type="file"
            accept="image/jpeg,image/png,image/webp,image/avif"
            hidden
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) void upload(file);
              e.target.value = "";
            }}
          />
          <Button size="sm" variant="soft" iconStart={<Upload aria-hidden="true" />} loading={pending} onClick={() => input.current?.click()}>
            Upload new
          </Button>
        </div>
        {media.error && <ErrorState message={media.error} onRetry={media.reload} />}
        {media.loading && <p className={styles.hint}>Loading images…</p>}
        {media.data && media.data.length === 0 && <p className={styles.hint}>No images yet — upload one.</p>}
        <div className={styles.mediaGrid}>
          {media.data?.map((asset) => (
            <button
              key={asset.id}
              type="button"
              className={styles.mediaTile}
              onClick={() => {
                onSelect(asset);
                onClose();
              }}
            >
              <span className={styles.mediaPreview}>
                <MediaThumb url={asset.url} alt={asset.alt_text ?? ""} />
              </span>
              <span className={styles.mediaCaption}>{asset.alt_text || asset.original_filename || "Untitled"}</span>
            </button>
          ))}
        </div>
      </div>
    </Dialog>
  );
}

/** A single-image field: preview + choose/remove. Loads the preview for an existing id. */
export function MediaField({
  label,
  hint,
  value,
  onChange,
  purpose,
}: {
  label: string;
  hint?: string;
  value: string | null;
  onChange: (id: string | null, asset?: MediaAsset) => void;
  purpose: string;
}) {
  const [open, setOpen] = useState(false);
  const [asset, setAsset] = useState<MediaAsset | null>(null);

  useEffect(() => {
    if (!value) {
      setAsset(null);
      return;
    }
    if (asset?.id === value) return;
    adminApi.mediaAsset(value).then(setAsset).catch(() => setAsset(null));
  }, [value, asset?.id]);

  return (
    <div className={styles.field}>
      <span className={styles.label}>{label}</span>
      <div className={styles.mediaField}>
        <span className={styles.mediaFieldPreview}>{asset && <MediaThumb url={asset.url} alt={asset.alt_text ?? ""} />}</span>
        <div className={styles.actions}>
          <Button size="sm" variant="soft" iconStart={<ImagePlus aria-hidden="true" />} onClick={() => setOpen(true)}>
            {value ? "Change" : "Choose image"}
          </Button>
          {value && (
            <Button size="sm" variant="ghost" iconStart={<X aria-hidden="true" />} onClick={() => onChange(null)}>
              Remove
            </Button>
          )}
        </div>
      </div>
      {hint && <p className={styles.hint}>{hint}</p>}
      <MediaPicker
        open={open}
        onClose={() => setOpen(false)}
        purpose={purpose}
        onSelect={(selected) => {
          setAsset(selected);
          onChange(selected.id, selected);
        }}
      />
    </div>
  );
}

/** Search the catalogue and add products (drafts included) to an ordering. */
export function ProductPicker({
  open,
  onClose,
  excludeIds,
  onAdd,
}: {
  open: boolean;
  onClose: () => void;
  excludeIds: string[];
  onAdd: (products: AdminProductSummary[]) => void;
}) {
  const [search, setSearch] = useState("");
  const [term, setTerm] = useState("");
  const [picked, setPicked] = useState<AdminProductSummary[]>([]);
  const results = useResource(() => adminApi.products({ q: term || undefined, page_size: 40 }), `${open}-${term}`);

  useEffect(() => {
    const t = window.setTimeout(() => setTerm(search.trim()), 250);
    return () => window.clearTimeout(t);
  }, [search]);

  const toggle = (p: AdminProductSummary) =>
    setPicked((list) => (list.some((x) => x.id === p.id) ? list.filter((x) => x.id !== p.id) : [...list, p]));

  return (
    <Dialog
      open={open}
      onClose={() => {
        setPicked([]);
        onClose();
      }}
      title="Add products"
      footer={
        <Button
          fullWidth
          disabled={picked.length === 0}
          onClick={() => {
            onAdd(picked);
            setPicked([]);
            onClose();
          }}
        >
          Add {picked.length || ""} product{picked.length === 1 ? "" : "s"}
        </Button>
      }
    >
      <div className={styles.stack}>
        <div className={styles.prefixed}>
          <Search size={16} className={styles.prefix} aria-hidden="true" />
          <input
            className={styles.input}
            placeholder="Search by name or SKU"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label="Search products"
          />
        </div>
        {results.error && <ErrorState message={results.error} onRetry={results.reload} />}
        <ul className={styles.list}>
          {results.data?.items
            .filter((p) => !excludeIds.includes(p.id))
            .map((p) => (
              <li key={p.id}>
                <label className={styles.checkItem} style={{ padding: "var(--space-1) 0" }}>
                  <input type="checkbox" checked={picked.some((x) => x.id === p.id)} onChange={() => toggle(p)} />
                  <span className={styles.thumb}>
                    <MediaThumb url={p.primary_image?.url} />
                  </span>
                  <span style={{ flex: 1 }}>
                    {p.name}
                    <span className={styles.hint}> · {p.status} · {formatMoney(p.price.selling_price)}</span>
                  </span>
                </label>
              </li>
            ))}
        </ul>
        {results.data && results.data.items.length === 0 && <p className={styles.hint}>No products found.</p>}
      </div>
    </Dialog>
  );
}
