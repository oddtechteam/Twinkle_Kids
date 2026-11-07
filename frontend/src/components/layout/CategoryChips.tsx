"use client";

import Link from "next/link";

import styles from "./CategoryBar.module.css";
import { useActiveNav } from "./useActiveNav";

export interface ChipLink {
  label: string;
  href: string;
  /** Rose accent text when not active (e.g. "New in"). */
  highlight?: boolean;
}

/**
 * Category strip links with the current page marked. Matching is query-aware, so
 * `/shop?sort=newest` marks "New in" and plain `/shop` marks "Shop all". Product pages mark
 * nothing here (they are not a category listing). Reads the URL: render under <Suspense>.
 */
export function CategoryChips({ links }: { links: ChipLink[] }) {
  const { active, onNavigate } = useActiveNav(
    links.map((link) => link.href),
    { shopChildren: false },
  );
  return (
    <>
      {links.map((link) => (
        <li key={link.href}>
          <Link
            href={link.href}
            className={`${styles.chip} ${link.highlight ? styles.highlight : ""}`}
            aria-current={link.href === active ? "page" : undefined}
            onClick={(event) => onNavigate(link.href, event)}
          >
            {link.label}
          </Link>
        </li>
      ))}
    </>
  );
}
