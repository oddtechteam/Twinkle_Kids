"use client";

import type { ReactNode } from "react";

import { ToastProvider } from "@/components/ui/Toast";
import { BagProvider } from "@/lib/bag/BagProvider";
import { WishlistProvider } from "@/lib/wishlist/WishlistProvider";

export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <ToastProvider>
      <WishlistProvider>
        <BagProvider>{children}</BagProvider>
      </WishlistProvider>
    </ToastProvider>
  );
}
