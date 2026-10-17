"use client";

import Link from "next/link";
import { Heart, Search, ShoppingBag, UserRound } from "lucide-react";
import { useState } from "react";

import { SearchDialog } from "@/components/search/SearchDialog";
import { useBag } from "@/lib/bag/BagProvider";
import { useWishlist } from "@/lib/wishlist/WishlistProvider";
import styles from "./HeaderActions.module.css";

function Count({ value, label }: { value: number; label: string }) {
  if (value <= 0) return null;
  return (
    <span className={styles.count}>
      <span aria-hidden="true">{value > 99 ? "99+" : value}</span>
      <span className="visually-hidden">{`, ${value} ${label}`}</span>
    </span>
  );
}

export function HeaderActions() {
  const [searchOpen, setSearchOpen] = useState(false);
  const wishlist = useWishlist();
  const bag = useBag();

  return (
    <div className={styles.actions}>
      <button
        type="button"
        className={`${styles.action} ${styles.search}`}
        onClick={() => setSearchOpen(true)}
        aria-haspopup="dialog"
      >
        <Search aria-hidden="true" size={21} strokeWidth={1.9} />
        <span className={styles.searchLabel}>Search</span>
      </button>
      <Link href="/account" className={`${styles.action} ${styles.hideSmall}`} aria-label="Account">
        <UserRound aria-hidden="true" size={21} strokeWidth={1.9} />
      </Link>
      <Link href="/wishlist" className={`${styles.action} ${styles.hideTiny}`} aria-label="Wishlist">
        <Heart aria-hidden="true" size={21} strokeWidth={1.9} />
        <Count value={wishlist.slugs.length} label="saved items" />
      </Link>
      <Link href="/bag" className={styles.action} aria-label="Shopping bag">
        <ShoppingBag aria-hidden="true" size={21} strokeWidth={1.9} />
        <Count value={bag.count} label="items in bag" />
      </Link>
      <SearchDialog open={searchOpen} onClose={() => setSearchOpen(false)} />
    </div>
  );
}
