"use client";

import { Crop, RefreshCw, Trash2, Upload } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { AdminPage, ConfirmDialog, ErrorState, LoadingState, TextInput, adminStyles as styles } from "@/components/admin/Kit";
import { ImageCropDialog } from "@/components/admin/ImageCropper";
import { FramedThumb, MEDIA_PURPOSES, MediaThumb } from "@/components/admin/Pickers";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { adminApi } from "@/lib/admin/api";
import { useMutation, useResource } from "@/lib/admin/hooks";
import type { MediaAsset } from "@/lib/admin/types";
import { formatDateTime } from "@/lib/format";
import { FRAMES, FRAME_NAMES, type ImageFrame } from "@/lib/media/frames";

const PAGE = 48;

/** Frames each library purpose is normally shown in; listed first in the crop section. */
const PURPOSE_FRAMES: Record<string, ImageFrame[]> = {
  product_image: ["product"],
  category_image: ["category"],
  collection_image: ["collection", "banner"],
  homepage_banner: ["hero", "banner"],
};

function CropSection({ asset, onChanged }: { asset: MediaAsset; onChanged: (asset: MediaAsset) => void }) {
  const [editing, setEditing] = useState<ImageFrame | null>(null);
  const primary = PURPOSE_FRAMES[asset.purpose] ?? [];
  const frames = [...primary, ...FRAME_NAMES.filter((f) => !primary.includes(f))];

  return (
    <div className={styles.stack}>
      <div>
        <span className={styles.label}>Storefront crops</span>
        <p className={styles.hint}>
          Each frame keeps its own crop. The original file is never changed, so you can re-crop at any time.
        </p>
      </div>
      <ul className={styles.cropList}>
        {frames.map((frame) => {
          const crop = asset.crops?.[frame];
          return (
            <li key={frame} className={styles.cropItem}>
              <span className={styles.cropThumb}>
                <FramedThumb asset={asset} frame={frame} />
              </span>
              <span className={styles.cropText}>
                <strong>
                  {FRAMES[frame].label} · {FRAMES[frame].ratioWidth}:{FRAMES[frame].ratioHeight}
                </strong>
                <span className={styles.hint}>{crop ? `Cropped ${formatDateTime(crop.updated_at)}` : "Centred automatically"}</span>
              </span>
              <Button size="sm" variant={crop ? "outline" : "soft"} iconStart={<Crop aria-hidden="true" />} onClick={() => setEditing(frame)}>
                {crop ? "Edit" : "Crop"}
              </Button>
            </li>
          );
        })}
      </ul>
      {editing && <ImageCropDialog open asset={asset} frame={editing} onClose={() => setEditing(null)} onSaved={onChanged} />}
    </div>
  );
}
const ACCEPT = "image/jpeg,image/png,image/webp,image/avif";

function kb(bytes: number) {
  return bytes >= 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.round(bytes / 1024)} KB`;
}

function AssetDialog({
  asset,
  onClose,
  onChanged,
  onDeleted,
}: {
  asset: MediaAsset;
  onClose: () => void;
  onChanged: (asset: MediaAsset) => void;
  onDeleted: (id: string) => void;
}) {
  const [alt, setAlt] = useState(asset.alt_text ?? "");
  const [confirmDelete, setConfirmDelete] = useState(false);
  const usage = useResource(() => adminApi.mediaUsage(asset.id), asset.id);
  const { run, pending } = useMutation();
  const replaceInput = useRef<HTMLInputElement>(null);

  return (
    <Dialog open onClose={onClose} title={asset.original_filename || "Image"}>
      <div className={styles.stack}>
        <span className={styles.mediaPreview} style={{ maxWidth: "20rem" }}>
          <MediaThumb url={asset.url} alt={asset.alt_text ?? ""} />
        </span>
        <p className={styles.hint}>
          {asset.width}×{asset.height}px · {kb(asset.size_bytes)} · {asset.content_type} · uploaded {formatDateTime(asset.created_at)}
        </p>
        {asset.visibility === "public" && <CropSection asset={asset} onChanged={onChanged} />}
        <TextInput label="Alt text" hint="Describe the image for screen readers and search engines." value={alt} onChange={setAlt} maxLength={300} />
        <div className={styles.actions}>
          <Button
            size="sm"
            loading={pending}
            disabled={alt === (asset.alt_text ?? "")}
            onClick={async () => {
              const res = await run(() => adminApi.updateMedia(asset.id, alt.trim() || null), { success: "Alt text saved" });
              if (res.ok) onChanged(res.result);
            }}
          >
            Save alt text
          </Button>
          <input
            ref={replaceInput}
            type="file"
            accept={ACCEPT}
            hidden
            onChange={async (e) => {
              const file = e.target.files?.[0];
              e.target.value = "";
              if (!file) return;
              const res = await run(() => adminApi.replaceMedia(asset.id, file), {
                success: "Image replaced everywhere it is used — crop it again for each frame",
              });
              if (res.ok) onChanged(res.result);
            }}
          />
          <Button size="sm" variant="outline" iconStart={<RefreshCw aria-hidden="true" />} onClick={() => replaceInput.current?.click()} disabled={pending}>
            Replace file
          </Button>
          <Button
            size="sm"
            variant="ghost"
            iconStart={<Trash2 aria-hidden="true" />}
            disabled={pending || usage.loading || usage.data?.in_use}
            onClick={() => setConfirmDelete(true)}
          >
            Delete
          </Button>
        </div>
        <div>
          <span className={styles.label}>Used in</span>
          {usage.error && <ErrorState message={usage.error} onRetry={usage.reload} />}
          {usage.loading && <LoadingState inline label="Checking where this image is used…" />}
          {usage.data && !usage.data.in_use && <p className={styles.hint}>Not used anywhere — safe to delete.</p>}
          {usage.data?.in_use && (
            <>
              <ul className={styles.hint}>
                {usage.data.places.map((p) => (
                  <li key={p}>{p}</li>
                ))}
              </ul>
              <p className={styles.hint}>Remove it from these places before deleting it.</p>
            </>
          )}
        </div>
      </div>
      <ConfirmDialog
        open={confirmDelete}
        title="Delete this image?"
        message="The file is removed from storage. This cannot be undone."
        confirmLabel="Delete image"
        destructive
        pending={pending}
        onClose={() => setConfirmDelete(false)}
        onConfirm={async () => {
          const res = await run(() => adminApi.deleteMedia(asset.id), { success: "Image deleted" });
          setConfirmDelete(false);
          if (res.ok) onDeleted(asset.id);
        }}
      />
    </Dialog>
  );
}

export default function MediaLibraryPage() {
  const [purpose, setPurpose] = useState("");
  const [uploadPurpose, setUploadPurpose] = useState("product_image");
  const [offset, setOffset] = useState(0);
  const [items, setItems] = useState<MediaAsset[]>([]);
  const [selected, setSelected] = useState<MediaAsset | null>(null);
  const page = useResource(() => adminApi.media({ purpose: purpose || undefined, limit: PAGE, offset }), `${purpose}-${offset}`);
  const { run, pending } = useMutation();
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!page.data) return;
    const data = page.data;
    setItems((prev) => (offset === 0 ? data : [...prev, ...data.filter((a) => !prev.some((p) => p.id === a.id))]));
  }, [page.data, offset]);

  const upload = async (files: FileList) => {
    for (const file of Array.from(files)) {
      const res = await run(() => adminApi.uploadMedia(file, uploadPurpose), { success: `Uploaded ${file.name}` });
      if (res.ok && (!purpose || purpose === uploadPurpose)) setItems((prev) => [res.result, ...prev]);
    }
  };

  return (
    <AdminPage
      title="Media library"
      description="JPEG, PNG, WebP or AVIF. Files are checked on the server before they are stored."
      breadcrumbs={[{ label: "Media" }]}
      actions={
        <>
          <select className={styles.select} style={{ width: "auto" }} value={uploadPurpose} onChange={(e) => setUploadPurpose(e.target.value)} aria-label="Upload as">
            {MEDIA_PURPOSES.map((p) => (
              <option key={p.value} value={p.value}>
                Upload as: {p.label}
              </option>
            ))}
          </select>
          <input
            ref={input}
            type="file"
            accept={ACCEPT}
            multiple
            hidden
            onChange={(e) => {
              if (e.target.files?.length) void upload(e.target.files);
              e.target.value = "";
            }}
          />
          <Button iconStart={<Upload aria-hidden="true" />} loading={pending} onClick={() => input.current?.click()}>
            Upload
          </Button>
        </>
      }
    >
      <div className={styles.stack}>
        <select
          className={styles.select}
          style={{ width: "auto" }}
          value={purpose}
          onChange={(e) => {
            setPurpose(e.target.value);
            setOffset(0);
          }}
          aria-label="Filter by type"
        >
          <option value="">All images</option>
          {MEDIA_PURPOSES.map((p) => (
            <option key={p.value} value={p.value}>
              {p.label}
            </option>
          ))}
        </select>
        {page.error && <ErrorState message={page.error} onRetry={page.reload} />}
        {page.loading && items.length === 0 && <LoadingState label="Loading images…" />}
        {!page.loading && items.length === 0 && !page.error && <p className={styles.hint}>No images yet.</p>}
        <div className={styles.mediaGrid}>
          {items.map((asset) => (
            <button key={asset.id} type="button" className={styles.mediaTile} onClick={() => setSelected(asset)}>
              <span className={styles.mediaPreview}>
                <MediaThumb url={asset.url} alt={asset.alt_text ?? ""} />
              </span>
              <span className={styles.mediaCaption}>{asset.alt_text || <em>No alt text</em>}</span>
            </button>
          ))}
        </div>
        {page.data && page.data.length === PAGE && (
          <div>
            <Button variant="outline" loading={page.loading} onClick={() => setOffset((o) => o + PAGE)}>
              Load more
            </Button>
          </div>
        )}
      </div>
      {selected && (
        <AssetDialog
          key={selected.id}
          asset={selected}
          onClose={() => setSelected(null)}
          onChanged={(asset) => {
            setSelected(asset);
            setItems((prev) => prev.map((a) => (a.id === asset.id ? asset : a)));
          }}
          onDeleted={(id) => {
            setSelected(null);
            setItems((prev) => prev.filter((a) => a.id !== id));
          }}
        />
      )}
    </AdminPage>
  );
}
