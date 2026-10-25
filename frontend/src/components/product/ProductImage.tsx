import Image from "next/image";

import type { ProductImage as ProductImageData } from "@/lib/api/types";
import { isRenderableImage } from "@/lib/catalog/adapters";
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
  className?: string;
}

export function ProductImage({
  image,
  name,
  seed,
  sizes,
  priority = false,
  ratio = "4 / 5",
  className,
}: ProductImageProps) {
  const art = artFor(seed, name);
  return (
    <div className={`${styles.frame} ${className ?? ""}`} style={{ aspectRatio: ratio }}>
      {image && isRenderableImage(image.url) ? (
        <Image
          src={image.url}
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
