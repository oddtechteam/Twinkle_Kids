import Link from "next/link";

import { Badge } from "@/components/ui/Badge";
import { Price } from "@/components/ui/Price";
import { type CardProduct, isRenderableImage } from "@/lib/catalog/adapters";
import { ProductImage } from "./ProductImage";
import { WishlistButton } from "./WishlistButton";
import styles from "./ProductCard.module.css";

interface ProductCardProps {
  product: CardProduct;
  priority?: boolean;
  sizes?: string;
  /** Hide the category label (e.g. inside a single-category listing). */
  hideLabel?: boolean;
}

export function ProductCard({
  product,
  priority = false,
  sizes = "(min-width: 1100px) 22vw, (min-width: 700px) 30vw, 46vw",
  hideLabel = false,
}: ProductCardProps) {
  const href = `/products/${product.slug}`;
  const discount = product.price.discount_amount !== null ? product.price.discount_percent : null;
  const hover = product.hoverImage && isRenderableImage(product.hoverImage.url) ? product.hoverImage : null;

  return (
    <article className={`${styles.card} ${product.inStock ? "" : styles.soldOut}`}>
      <div className={styles.media}>
        <ProductImage
          image={product.image}
          name={product.name}
          seed={product.slug}
          sizes={sizes}
          priority={priority}
          className={styles.image}
        />
        {hover && product.image && (
          // Decorative second view; the product is already named by the primary image.
          <div className={styles.hover} aria-hidden="true">
            <ProductImage image={{ ...hover, alt_text: "" }} name="" seed={product.slug} sizes={sizes} />
          </div>
        )}
        <div className={styles.badges}>
          {!product.inStock && <Badge tone="muted">Sold out</Badge>}
          {product.inStock && discount !== null && discount > 0 && !product.priceVaries && (
            <Badge tone="sale">-{discount}%</Badge>
          )}
          {product.badges.slice(0, 2).map((badge) => (
            <Badge key={badge} tone="navy">
              {badge}
            </Badge>
          ))}
        </div>
        <div className={styles.wishlist}>
          <WishlistButton slug={product.slug} name={product.name} />
        </div>
      </div>
      <div className={styles.body}>
        {!hideLabel && product.label && <p className={styles.label}>{product.label}</p>}
        <h3 className={styles.name}>
          <Link href={href} className={styles.link}>
            {product.name}
          </Link>
        </h3>
        <Price
          price={product.price}
          fromPrice={product.fromPrice}
          priceVaries={product.priceVaries}
          size="sm"
        />
      </div>
    </article>
  );
}

export function ProductCardSkeleton() {
  return (
    <div className={styles.skeleton} aria-hidden="true">
      <span className={styles.skeletonMedia} />
      <span className={styles.skeletonLine} />
      <span className={`${styles.skeletonLine} ${styles.short}`} />
    </div>
  );
}
