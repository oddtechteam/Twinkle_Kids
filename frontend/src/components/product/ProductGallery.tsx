"use client";

import Image from "next/image";
import { ChevronLeft, ChevronRight, Expand } from "lucide-react";
import { type MouseEvent, useEffect, useRef, useState } from "react";

import { Dialog } from "@/components/ui/Dialog";
import type { ProductImage as ProductImageData } from "@/lib/api/types";
import { isRenderableImage } from "@/lib/catalog/adapters";
import { ProductArt, artFor } from "./ProductArt";
import styles from "./ProductGallery.module.css";

interface GalleryProps {
  images: ProductImageData[];
  name: string;
  slug: string;
  /** Media for the currently selected colour, shown first when available. */
  focusVariantIds?: string[];
}

export function ProductGallery({ images, name, slug, focusVariantIds = [] }: GalleryProps) {
  const usable = images.filter((image) => isRenderableImage(image.url));
  const [active, setActive] = useState(0);
  const [zoomOpen, setZoomOpen] = useState(false);
  const [magnified, setMagnified] = useState<{ x: number; y: number } | null>(null);
  const track = useRef<HTMLDivElement>(null);

  // Jump to the first image of the selected colour when the selection changes.
  const focusKey = focusVariantIds.join(",");
  useEffect(() => {
    if (!focusKey) return;
    const ids = new Set(focusKey.split(","));
    const index = usable.findIndex((image) => image.variant_id && ids.has(image.variant_id));
    if (index >= 0) select(index);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- run only when the colour changes
  }, [focusKey]);

  function select(index: number) {
    setActive(index);
    const slide = track.current?.children[index] as HTMLElement | undefined;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    slide?.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "nearest", inline: "start" });
  }

  if (usable.length === 0) {
    const art = artFor(slug, name);
    return (
      <div className={styles.gallery}>
        <div className={styles.main}>
          <div className={styles.slideSingle}>
            <ProductArt kind={art.kind} tone={art.tone} label={`${name} — illustration, photo coming soon`} />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.gallery}>
      <div
        ref={track}
        className={styles.main}
        onScroll={(event) => {
          const el = event.currentTarget;
          const index = Math.round(el.scrollLeft / el.clientWidth);
          if (index !== active) setActive(index);
        }}
        aria-roledescription="carousel"
        aria-label={`${name} images`}
      >
        {usable.map((image, index) => (
          <div
            key={image.media_asset_id}
            className={styles.slide}
            role="group"
            aria-roledescription="slide"
            aria-label={`${index + 1} of ${usable.length}`}
          >
            <Image
              src={image.url}
              alt={image.alt_text ?? `${name} — image ${index + 1}`}
              fill
              loading={index === 0 ? "eager" : "lazy"}
              fetchPriority={index === 0 ? "high" : undefined}
              sizes="(min-width: 1024px) 50vw, 100vw"
              className={styles.image}
            />
          </div>
        ))}
      </div>

      <button
        type="button"
        className={styles.zoomButton}
        onClick={() => {
          setMagnified(null);
          setZoomOpen(true);
        }}
        aria-haspopup="dialog"
      >
        <Expand aria-hidden="true" size={18} />
        <span className="visually-hidden">Enlarge image {active + 1}</span>
      </button>

      <Dialog
        open={zoomOpen}
        onClose={() => setZoomOpen(false)}
        title={`${name} — image ${active + 1} of ${usable.length}`}
        hideTitle
      >
        <div className={styles.zoom}>
          <button
            type="button"
            className={`${styles.zoomStage} ${magnified ? styles.zoomed : ""}`}
            onClick={(event: MouseEvent<HTMLButtonElement>) => {
              if (magnified) return setMagnified(null);
              const box = event.currentTarget.getBoundingClientRect();
              setMagnified({
                x: ((event.clientX - box.left) / box.width) * 100,
                y: ((event.clientY - box.top) / box.height) * 100,
              });
            }}
            aria-label={magnified ? "Zoom out" : "Zoom in"}
          >
            {usable[active] && (
              <Image
                src={usable[active].url}
                alt={usable[active].alt_text ?? `${name} — image ${active + 1}`}
                fill
                sizes="(min-width: 900px) 70vw, 100vw"
                className={styles.zoomImage}
                style={magnified ? { transformOrigin: `${magnified.x}% ${magnified.y}%` } : undefined}
              />
            )}
          </button>
          {usable.length > 1 && (
            <div className={styles.zoomNav}>
              <button
                type="button"
                className={styles.zoomArrow}
                onClick={() => {
                  setMagnified(null);
                  select((active - 1 + usable.length) % usable.length);
                }}
                aria-label="Previous image"
              >
                <ChevronLeft aria-hidden="true" />
              </button>
              <span aria-live="polite">
                {active + 1} / {usable.length}
              </span>
              <button
                type="button"
                className={styles.zoomArrow}
                onClick={() => {
                  setMagnified(null);
                  select((active + 1) % usable.length);
                }}
                aria-label="Next image"
              >
                <ChevronRight aria-hidden="true" />
              </button>
            </div>
          )}
        </div>
      </Dialog>

      {usable.length > 1 && (
        <>
          <div className={styles.dots} aria-hidden="true">
            {usable.map((image, index) => (
              <span key={image.media_asset_id} className={`${styles.dot} ${index === active ? styles.dotActive : ""}`} />
            ))}
          </div>
          <ul className={styles.thumbs} aria-label="Choose image">
            {usable.map((image, index) => (
              <li key={image.media_asset_id}>
                <button
                  type="button"
                  className={`${styles.thumb} ${index === active ? styles.thumbActive : ""}`}
                  onClick={() => select(index)}
                  aria-label={`Show image ${index + 1}`}
                  aria-current={index === active ? "true" : undefined}
                >
                  <Image src={image.url} alt="" fill sizes="88px" className={styles.image} />
                </button>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
