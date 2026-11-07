import Link from "next/link";
import { Suspense } from "react";

import { listCategories, listCollections, topLevel } from "@/lib/catalog/api";
import type { LinkItem } from "@/lib/content/types";
import styles from "./CategoryBar.module.css";
import { type ChipLink, CategoryChips } from "./CategoryChips";

/** Category strip under the header — categories come from the catalogue API. */
export async function CategoryBar() {
  const result = await listCategories();
  const categories = result.ok ? topLevel(result.data) : [];
  if (categories.length === 0) return null;
  const links: ChipLink[] = [
    { label: "New in", href: "/shop?sort=newest", highlight: true },
    ...categories.map((category) => ({ label: category.name, href: `/category/${category.slug}` })),
    { label: "Shop all", href: "/shop" },
  ];
  return (
    <nav aria-label="Shop by category" className={styles.bar}>
      <ul className={`container ${styles.list}`}>
        {/* The active chip reads the URL on the client; plain chips are the static shell. */}
        <Suspense fallback={<StaticChips links={links} />}>
          <CategoryChips links={links} />
        </Suspense>
      </ul>
    </nav>
  );
}

function StaticChips({ links }: { links: ChipLink[] }) {
  return links.map((link) => (
    <li key={link.href}>
      <Link href={link.href} className={`${styles.chip} ${link.highlight ? styles.highlight : ""}`}>
        {link.label}
      </Link>
    </li>
  ));
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

/** Published collections for the desktop "Collections" dropdown (from the catalogue API). */
export async function CollectionsMenu() {
  const result = await listCollections();
  const collections = result.ok ? result.data : [];
  if (collections.length === 0) return null;
  return (
    <div className={styles.dropMenu}>
      <p className={styles.dropTitle}>Curated collections</p>
      <ul className={styles.dropList}>
        {collections.map((collection) => (
          <li key={collection.id}>
            <Link href={`/collections/${collection.slug}`} className={styles.dropLink}>
              <span className={styles.dropName}>{collection.name}</span>
              {collection.description && <span className={styles.dropCaption}>{collection.description}</span>}
            </Link>
          </li>
        ))}
      </ul>
      <Link href="/collections" className={styles.dropAll}>
        View all collections <span aria-hidden="true">→</span>
      </Link>
    </div>
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
