import Image from "next/image";

import type { ProductImage as ProductImageData } from "@/lib/api/types";
import { isRenderableImage } from "@/lib/catalog/adapters";
import { type ImageFrame, framedImage } from "@/lib/media/frames";
import { ProductArt, artFor } from "./ProductArt";
import styles from "./ProductImage.module.css";

interface ProductImageProps {
  image: ProductImageData | null;
  name: string;
  seed: string;
  sizes: string;
  priority?: boolean;
  /** CSS aspect-ratio of the frame, e.g. "4 / 5". The frame reserves space: no layout shift. */
  ratio?: string;
  /** Which admin crop to show; without one the original is centred (object-fit: cover). */
  frame?: ImageFrame;
  className?: string;
}

export function ProductImage({
  image,
  name,
  seed,
  sizes,
  priority = false,
  ratio = "4 / 5",
  frame = "product",
  className,
}: ProductImageProps) {
  const art = artFor(seed, name);
  const src = image ? framedImage(image, frame).url : null;
  return (
    <div className={`${styles.frame} ${className ?? ""}`} style={{ aspectRatio: ratio }}>
      {image && src && isRenderableImage(src) ? (
        <Image
          src={src}
          alt={image.alt_text ?? name}
          fill
          sizes={sizes}
          loading={priority ? "eager" : "lazy"}
          fetchPriority={priority ? "high" : undefined}
          className={styles.image}
        />
      ) : (
        <ProductArt kind={art.kind} tone={art.tone} label={`${name} — illustration, photo coming soon`} />
      )}
    </div>
  );
}
