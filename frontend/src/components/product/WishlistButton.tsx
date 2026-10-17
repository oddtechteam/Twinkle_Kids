"use client";

import { Heart } from "lucide-react";

import { useToast } from "@/components/ui/Toast";
import { useWishlist } from "@/lib/wishlist/WishlistProvider";
import styles from "./WishlistButton.module.css";

export function WishlistButton({
  slug,
  name,
  variant = "floating",
}: {
  slug: string;
  name: string;
  variant?: "floating" | "inline";
}) {
  const wishlist = useWishlist();
  const toast = useToast();
  const saved = wishlist.has(slug);

  return (
    <button
      type="button"
      className={`${styles.button} ${styles[variant]} ${saved ? styles.saved : ""}`}
      aria-pressed={saved}
      aria-label={saved ? `Remove ${name} from wishlist` : `Save ${name} to wishlist`}
      onClick={(event) => {
        event.preventDefault();
        const nowSaved = wishlist.toggle(slug);
        toast.show({
          title: nowSaved ? "Saved to your wishlist" : "Removed from your wishlist",
          description: name,
          tone: nowSaved ? "success" : "info",
        });
      }}
    >
      <Heart aria-hidden="true" size={variant === "inline" ? 20 : 18} strokeWidth={2} />
      {variant === "inline" && <span>{saved ? "Saved" : "Save"}</span>}
    </button>
  );
}
