import Link from "next/link";

import { listCategories, listCollections, topLevel } from "@/lib/catalog/api";
import type { LinkItem } from "@/lib/content/types";
import styles from "./CategoryBar.module.css";

/** Category strip under the header — categories come from the catalogue API. */
export async function CategoryBar() {
  const result = await listCategories();
  const categories = result.ok ? topLevel(result.data) : [];
  if (categories.length === 0) return null;
  return (
    <nav aria-label="Shop by category" className={styles.bar}>
      <ul className={`container ${styles.list}`}>
        <li>
          <Link href="/shop?sort=newest" className={`${styles.chip} ${styles.highlight}`}>
            New in
          </Link>
        </li>
        {categories.map((category) => (
          <li key={category.id}>
            <Link href={`/category/${category.slug}`} className={styles.chip}>
              {category.name}
            </Link>
          </li>
        ))}
        <li>
          <Link href="/shop" className={styles.chip}>
            Shop all
          </Link>
        </li>
      </ul>
    </nav>
  );
}

/** Instant fallback while categories stream in (and when the API is unreachable). */
export function CategoryBarFallback({ links }: { links: LinkItem[] }) {
  return (
    <nav aria-label="Shop" className={styles.bar}>
      <ul className={`container ${styles.list}`}>
        {links.map((link) => (
          <li key={link.href}>
            <Link href={link.href} className={styles.chip}>
              {link.label}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}

/** Category and collection links for the mobile menu drawer (both from the catalogue API). */
export async function CategoryMenuList() {
  const [categoryResult, collectionResult] = await Promise.all([listCategories(), listCollections()]);
  const categories = categoryResult.ok ? topLevel(categoryResult.data) : [];
  const collections = collectionResult.ok ? collectionResult.data : [];
  if (categories.length === 0 && collections.length === 0) return null;
  return (
    <>
      {categories.length > 0 && (
        <div className={styles.menu}>
          <p className={styles.menuTitle}>Shop by category</p>
          <ul className={styles.menuList}>
            {categories.map((category) => (
              <li key={category.id}>
                <Link href={`/category/${category.slug}`} className={styles.menuLink}>
                  {category.name}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}
      {collections.length > 0 && (
        <div className={styles.menu}>
          <p className={styles.menuTitle}>Collections</p>
          <ul className={styles.menuList}>
            {collections.map((collection) => (
              <li key={collection.id}>
                <Link href={`/collections/${collection.slug}`} className={styles.menuLink}>
                  {collection.name}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}
    </>
  );
}
