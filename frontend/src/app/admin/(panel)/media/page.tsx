"use client";

import { RefreshCw, Trash2, Upload } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { AdminPage, ConfirmDialog, ErrorState, TextInput, adminStyles as styles } from "@/components/admin/Kit";
import { MEDIA_PURPOSES, MediaThumb } from "@/components/admin/Pickers";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { adminApi } from "@/lib/admin/api";
import { useMutation, useResource } from "@/lib/admin/hooks";
import type { MediaAsset } from "@/lib/admin/types";
import { formatDateTime } from "@/lib/format";

const PAGE = 48;
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
              const res = await run(() => adminApi.replaceMedia(asset.id, file), { success: "Image replaced everywhere it is used" });
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
          {usage.loading && <p className={styles.hint}>Checking…</p>}
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
