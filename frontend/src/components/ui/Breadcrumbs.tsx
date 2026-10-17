import Link from "next/link";
import { ChevronRight } from "lucide-react";

import styles from "./Breadcrumbs.module.css";

export interface Crumb {
  label: string;
  href?: string;
}

export function Breadcrumbs({ items }: { items: Crumb[] }) {
  return (
    <nav aria-label="Breadcrumb" className={styles.nav}>
      <ol className={styles.list}>
        {items.map((item, index) => {
          const last = index === items.length - 1;
          return (
            <li key={`${item.label}-${index}`} className={styles.item}>
              {item.href && !last ? (
                <Link href={item.href} className={styles.link}>
                  {item.label}
                </Link>
              ) : (
                <span aria-current={last ? "page" : undefined} className={styles.current}>
                  {item.label}
                </span>
              )}
              {!last && <ChevronRight aria-hidden="true" size={14} className={styles.sep} />}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
