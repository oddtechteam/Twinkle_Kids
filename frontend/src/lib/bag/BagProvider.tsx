"use client";

import { createContext, type ReactNode, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";

import type { Cart } from "@/lib/api/types";
import {
  acknowledgeCartPrices,
  addCartItem,
  bagErrorMessage,
  fetchCart,
  removeCartItem,
  updateCartItem,
} from "./api";

/**
 * Shopping bag state for the whole storefront, backed by the server-side cart API.
 *
 * The backend owns prices, stock checks and totals: this provider only keeps the latest cart
 * the API returned. Guests are identified by an HttpOnly cookie; after signing in, the API
 * merges the guest bag into the account bag on the next request (`refresh`).
 */

export type BagResult = { ok: true } | { ok: false; message: string };

interface BagApi {
  status: "loading" | "ready" | "error";
  cart: Cart | null;
  count: number;
  add: (variantId: string, quantity: number) => Promise<BagResult>;
  update: (itemId: string, quantity: number) => Promise<BagResult>;
  remove: (itemId: string) => Promise<BagResult>;
  acknowledgePrices: () => Promise<BagResult>;
  refresh: () => Promise<void>;
}

const BagContext = createContext<BagApi | null>(null);

export function BagProvider({ children }: { children: ReactNode }) {
  const [cart, setCart] = useState<Cart | null>(null);
  const [status, setStatus] = useState<BagApi["status"]>("loading");
  const latest = useRef(0); // ignore responses that arrive after a newer request

  const run = useCallback(async (request: () => Promise<Cart>): Promise<BagResult> => {
    const ticket = ++latest.current;
    try {
      const next = await request();
      if (ticket === latest.current) {
        setCart(next);
        setStatus("ready");
      }
      return { ok: true };
    } catch (error) {
      return { ok: false, message: bagErrorMessage(error) };
    }
  }, []);

  const refresh = useCallback(async () => {
    const result = await run(fetchCart);
    if (!result.ok) setStatus((current) => (current === "ready" ? current : "error"));
  }, [run]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- loads external data (API / session storage) on mount
    void refresh();
    // Keep the header count honest when the bag changes in another tab.
    const onFocus = () => void refresh();
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, [refresh]);

  const api = useMemo<BagApi>(
    () => ({
      status,
      cart,
      count: cart?.item_count ?? 0,
      add: (variantId, quantity) => run(() => addCartItem(variantId, quantity)),
      update: (itemId, quantity) => run(() => updateCartItem(itemId, quantity)),
      remove: (itemId) => run(() => removeCartItem(itemId)),
      acknowledgePrices: () => run(acknowledgeCartPrices),
      refresh,
    }),
    [cart, status, run, refresh],
  );
  return <BagContext.Provider value={api}>{children}</BagContext.Provider>;
}

export function useBag(): BagApi {
  const api = useContext(BagContext);
  if (!api) throw new Error("useBag must be used inside <BagProvider>");
  return api;
}
