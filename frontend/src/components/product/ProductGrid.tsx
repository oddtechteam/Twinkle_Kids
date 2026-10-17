import type { CardProduct } from "@/lib/catalog/adapters";
import { ProductCard, ProductCardSkeleton } from "./ProductCard";
import styles from "./ProductGrid.module.css";

export function ProductGrid({
  products,
  columns = 4,
  priorityCount = 0,
}: {
  products: CardProduct[];
  columns?: 3 | 4;
  priorityCount?: number;
}) {
  return (
    <ul className={`${styles.grid} ${styles[`cols${columns}`]}`}>
      {products.map((product, index) => (
        <li key={product.slug} className={styles.item}>
          <ProductCard product={product} priority={index < priorityCount} />
        </li>
      ))}
    </ul>
  );
}

export function ProductGridSkeleton({ count = 8, columns = 4 }: { count?: number; columns?: 3 | 4 }) {
  return (
    <ul className={`${styles.grid} ${styles[`cols${columns}`]}`} aria-hidden="true">
      {Array.from({ length: count }, (_, i) => (
        <li key={i} className={styles.item}>
          <ProductCardSkeleton />
        </li>
      ))}
    </ul>
  );
}
