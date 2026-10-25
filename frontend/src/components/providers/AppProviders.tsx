"use client";

import type { ReactNode } from "react";

import { NavigationProgressProvider } from "@/components/layout/NavigationProgress";
import { ToastProvider } from "@/components/ui/Toast";
import { BagProvider } from "@/lib/bag/BagProvider";
import { WishlistProvider } from "@/lib/wishlist/WishlistProvider";

export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <NavigationProgressProvider>
      <ToastProvider>
        <WishlistProvider>
          <BagProvider>{children}</BagProvider>
        </WishlistProvider>
      </ToastProvider>
    </NavigationProgressProvider>
  );
}
