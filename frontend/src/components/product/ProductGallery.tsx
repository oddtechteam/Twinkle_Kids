"use client";

import Image from "next/image";
import { useEffect, useRef, useState } from "react";

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
              priority={index === 0}
              sizes="(min-width: 1024px) 50vw, 100vw"
              className={styles.image}
            />
          </div>
        ))}
      </div>

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
