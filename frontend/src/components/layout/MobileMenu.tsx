"use client";

import Link from "next/link";
import { Heart, Menu, ShoppingBag, UserRound } from "lucide-react";
import { type ReactNode, useState } from "react";

import { Logo } from "@/components/brand/Logo";
import { Dialog } from "@/components/ui/Dialog";
import { Motif } from "@/components/ui/Motif";
import type { LinkItem } from "@/lib/content/types";
import styles from "./MobileMenu.module.css";

interface MobileMenuProps {
  links: LinkItem[];
  tagline: string;
  brandName: string;
  /** Server-rendered category links (streamed). */
  children?: ReactNode;
}

export function MobileMenu({ links, tagline, brandName, children }: MobileMenuProps) {
  const [open, setOpen] = useState(false);
  const close = () => setOpen(false);

  return (
    <>
      <button
        type="button"
        className={styles.trigger}
        onClick={() => setOpen(true)}
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-label="Open menu"
      >
        <Menu aria-hidden="true" size={24} strokeWidth={1.9} />
      </button>

      <Dialog open={open} onClose={close} title="Menu" hideTitle variant="drawer-start">
        {/* Any link click inside the drawer (including streamed category links) closes it. */}
        <div
          className={styles.content}
          onClick={(event) => {
            if ((event.target as HTMLElement).closest("a")) close();
          }}
        >
          <div className={styles.brand}>
            <Logo name={brandName} />
            <p className={styles.tagline}>
              <Motif size={11} /> {tagline}
            </p>
          </div>

          <nav aria-label="Mobile">
            <ul className={styles.primary}>
              {links.map((link) => (
                <li key={link.href}>
                  <Link href={link.href} className={styles.primaryLink}>
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>

          {children}

          <ul className={styles.secondary}>
            <li>
              <Link href="/account" className={styles.secondaryLink}>
                <UserRound aria-hidden="true" size={20} /> Account
              </Link>
            </li>
            <li>
              <Link href="/wishlist" className={styles.secondaryLink}>
                <Heart aria-hidden="true" size={20} /> Wishlist
              </Link>
            </li>
            <li>
              <Link href="/bag" className={styles.secondaryLink}>
                <ShoppingBag aria-hidden="true" size={20} /> Shopping bag
              </Link>
            </li>
          </ul>
        </div>
      </Dialog>
    </>
  );
}
