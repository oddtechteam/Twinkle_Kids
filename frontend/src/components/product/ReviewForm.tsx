"use client";

import Link from "next/link";
import { ImagePlus, Star, X } from "lucide-react";
import { type FormEvent, useEffect, useState } from "react";

import { Button } from "@/components/ui/Button";
import { TextField } from "@/components/ui/Form";
import { fetchMe } from "@/lib/account/api";
import { ApiError, apiFetch } from "@/lib/api/client";
import styles from "./ReviewForm.module.css";

const MAX_PHOTOS = 3;
const MAX_BYTES = 5 * 1024 * 1024; // matches the API default (MEDIA_MAX_UPLOAD_BYTES)
const TYPES = ["image/jpeg", "image/png", "image/webp", "image/avif"];

type Viewer = "loading" | "guest" | "customer";

/** Signed-in customers can leave a review; it's moderated by the shop before it appears. */
export function ReviewForm({ slug, productName }: { slug: string; productName: string }) {
  const [viewer, setViewer] = useState<Viewer>("loading");
  const [open, setOpen] = useState(false);
  const [rating, setRating] = useState(0);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [photos, setPhotos] = useState<File[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    let live = true;
    fetchMe()
      .then((me) => live && setViewer(me ? "customer" : "guest"))
      .catch(() => live && setViewer("guest"));
    return () => {
      live = false;
    };
  }, []);

  function addPhotos(files: FileList | null) {
    if (!files) return;
    const picked = [...photos];
    for (const file of Array.from(files)) {
      if (picked.length >= MAX_PHOTOS) break;
      if (!TYPES.includes(file.type)) {
        setError("Photos must be JPEG, PNG, WebP or AVIF.");
        continue;
      }
      if (file.size > MAX_BYTES) {
        setError("Each photo must be under 5 MB.");
        continue;
      }
      picked.push(file);
    }
    setPhotos(picked);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (rating < 1) {
      setError("Choose a star rating.");
      return;
    }
    setError(null);
    setPending(true);
    const form = new FormData();
    form.set("rating", String(rating));
    if (title.trim()) form.set("title", title.trim());
    if (body.trim()) form.set("body", body.trim());
    for (const photo of photos) form.append("photos", photo);
    try {
      const res = await apiFetch<{ detail: string }>(`/products/${encodeURIComponent(slug)}/reviews`, {
        method: "POST",
        body: form,
        timeoutMs: 60000,
      });
      setDone(res.detail);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "We couldn't send your review. Please try again.");
    } finally {
      setPending(false);
    }
  }

  if (viewer === "loading") return null;
  if (viewer === "guest") {
    return (
      <p className={styles.note}>
        <Link href={`/account?next=/products/${slug}`}>Sign in</Link> to review this product.
      </p>
    );
  }
  if (done) {
    return (
      <p className={styles.success} role="status">
        {done}
      </p>
    );
  }
  if (!open) {
    return (
      <Button variant="outline" onClick={() => setOpen(true)}>
        Write a review
      </Button>
    );
  }

  return (
    <form className={styles.form} onSubmit={submit} noValidate aria-label={`Review ${productName}`}>
      <fieldset className={styles.rating}>
        <legend className={styles.label}>Your rating</legend>
        {[1, 2, 3, 4, 5].map((n) => (
          <label key={n} className={styles.star} data-on={n <= rating}>
            <input type="radio" name="rating" value={n} checked={rating === n} onChange={() => setRating(n)} className="visually-hidden" />
            <Star aria-hidden="true" size={26} />
            <span className="visually-hidden">
              {n} {n === 1 ? "star" : "stars"}
            </span>
          </label>
        ))}
      </fieldset>
      <TextField label="Headline (optional)" value={title} onChange={(e) => setTitle(e.target.value)} maxLength={120} />
      <label className={styles.field}>
        <span className={styles.label}>Your review (optional)</span>
        <textarea className={styles.textarea} value={body} onChange={(e) => setBody(e.target.value)} maxLength={2000} rows={4} />
      </label>
      <div className={styles.photos}>
        {photos.map((photo, index) => (
          <span key={`${photo.name}-${index}`} className={styles.photo}>
            {photo.name}
            <button type="button" aria-label={`Remove photo ${index + 1}`} onClick={() => setPhotos(photos.filter((_, i) => i !== index))}>
              <X size={14} aria-hidden="true" />
            </button>
          </span>
        ))}
        {photos.length < MAX_PHOTOS && (
          <label className={styles.addPhoto}>
            <ImagePlus size={16} aria-hidden="true" /> Add photo{photos.length ? "" : "s"} (up to {MAX_PHOTOS})
            <input
              type="file"
              accept={TYPES.join(",")}
              multiple
              className="visually-hidden"
              onChange={(e) => {
                addPhotos(e.target.files);
                e.target.value = "";
              }}
            />
          </label>
        )}
      </div>
      <p className={styles.note}>Reviews and photos are checked by the shop before they appear.</p>
      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}
      <div className={styles.actions}>
        <Button type="submit" loading={pending}>
          Submit review
        </Button>
        <Button variant="ghost" onClick={() => setOpen(false)} disabled={pending}>
          Cancel
        </Button>
      </div>
    </form>
  );
}
