"use client";

import { createContext, type ReactNode, useContext, useMemo } from "react";

/**
 * Shopping bag integration point.
 *
 * The server-side cart API (prices and totals calculated by the backend) arrives with the
 * cart & checkout phase. Until then the bag is honestly unavailable: the count is 0 and
 * `add` reports that adding is not possible yet — nothing is faked or stored locally.
 */

export type AddToBagResult = { ok: true } | { ok: false; reason: "unavailable" | "error" };

interface BagApi {
  available: boolean;
  count: number;
  add: (variantId: string, quantity: number) => Promise<AddToBagResult>;
}

const BagContext = createContext<BagApi | null>(null);

export function BagProvider({ children }: { children: ReactNode }) {
  const api = useMemo<BagApi>(
    () => ({
      available: false,
      count: 0,
      add: async () => ({ ok: false, reason: "unavailable" }),
    }),
    [],
  );
  return <BagContext.Provider value={api}>{children}</BagContext.Provider>;
}

export function useBag(): BagApi {
  const api = useContext(BagContext);
  if (!api) throw new Error("useBag must be used inside <BagProvider>");
  return api;
}
