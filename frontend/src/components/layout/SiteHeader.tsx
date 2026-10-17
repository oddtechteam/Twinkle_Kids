import Link from "next/link";
import { Suspense } from "react";

import { Logo } from "@/components/brand/Logo";
import type { SiteContent } from "@/lib/content/types";
import { CategoryBar, CategoryBarFallback, CategoryMenuList } from "./CategoryBar";
import { HeaderActions } from "./HeaderActions";
import { MobileMenu } from "./MobileMenu";
import styles from "./SiteHeader.module.css";

export function SiteHeader({ content }: { content: SiteContent }) {
  const primary = content.navigation.primary;
  return (
    <header className={styles.header}>
      <div className={`container ${styles.row}`}>
        <div className={styles.start}>
          <MobileMenu
            links={content.navigation.mobile}
            tagline={content.brand.tagline}
            brandName={content.brand.name}
          >
            <Suspense fallback={null}>
              <CategoryMenuList />
            </Suspense>
          </MobileMenu>
          <Logo name={content.brand.name} image={content.brand.logo} />
        </div>

        <nav aria-label="Main" className={styles.nav}>
          <ul className={styles.navList}>
            {primary.map((link) => (
              <li key={link.href}>
                <Link href={link.href} className={styles.navLink}>
                  {link.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        <HeaderActions />
      </div>

      <Suspense fallback={<CategoryBarFallback links={primary} />}>
        <CategoryBar />
      </Suspense>
    </header>
  );
}
