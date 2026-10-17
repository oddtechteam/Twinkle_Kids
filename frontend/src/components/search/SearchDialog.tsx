"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, Search } from "lucide-react";
import { type FormEvent, useEffect, useId, useRef, useState } from "react";

import { ProductImage } from "@/components/product/ProductImage";
import { Dialog } from "@/components/ui/Dialog";
import { Price } from "@/components/ui/Price";
import { apiFetch } from "@/lib/api/client";
import type { ProductList, ProductSummary } from "@/lib/api/types";
import styles from "./SearchDialog.module.css";

const MIN_QUERY = 2;
const SUGGESTION_LIMIT = 6;

const QUICK_LINKS = [
  { label: "New arrivals", href: "/shop?sort=newest" },
  { label: "Shop all", href: "/shop" },
  { label: "Wishlist", href: "/wishlist" },
];

type State =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "done"; items: ProductSummary[]; total: number }
  | { status: "error" };

export function SearchDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [state, setState] = useState<State>({ status: "idle" });
  const inputId = useId();
  const resultsId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const term = query.trim();

  // The dialog opens after mount, so focus the field explicitly each time it opens.
  useEffect(() => {
    if (!open) return;
    const frame = window.requestAnimationFrame(() => inputRef.current?.focus());
    return () => window.cancelAnimationFrame(frame);
  }, [open]);

  // Debounced suggestions from the live catalogue API (browser → NEXT_PUBLIC_API_BASE_URL).
  useEffect(() => {
    if (term.length < MIN_QUERY) {
      setState({ status: "idle" });
      return;
    }
    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      setState({ status: "loading" });
      try {
        const params = new URLSearchParams({ q: term, page_size: String(SUGGESTION_LIMIT) });
        const data = await apiFetch<ProductList>(`/products?${params.toString()}`, {
          signal: controller.signal,
        });
        setState({ status: "done", items: data.items, total: data.total });
      } catch {
        if (!controller.signal.aborted) setState({ status: "error" });
      }
    }, 250);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [term]);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!term) return;
    onClose();
    router.push(`/search?q=${encodeURIComponent(term)}`);
  };

  return (
    <Dialog open={open} onClose={onClose} title="Search Twinkle Kids" hideTitle variant="top">
      <div className={`container-narrow ${styles.wrap}`}>
        <form role="search" onSubmit={submit} className={styles.form}>
          <label htmlFor={inputId} className="visually-hidden">
            Search products
          </label>
          <Search aria-hidden="true" size={24} className={styles.formIcon} />
          <input
            ref={inputRef}
            id={inputId}
            type="search"
            className={styles.input}
            placeholder="Search dresses, tees, party wear…"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            autoComplete="off"
            maxLength={100}
            aria-controls={resultsId}
          />
          <button type="submit" className={styles.submit} disabled={!term}>
            Search
          </button>
        </form>

        <div id={resultsId} className={styles.results} aria-live="polite">
          {state.status === "idle" && (
            <div className={styles.quick}>
              <p className={styles.heading}>Quick links</p>
              <ul className={styles.quickList}>
                {QUICK_LINKS.map((link) => (
                  <li key={link.href}>
                    <Link href={link.href} className={styles.quickLink} onClick={onClose}>
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {state.status === "loading" && <p className={styles.note}>Searching…</p>}
          {state.status === "error" && (
            <p className={styles.note}>Search is unavailable right now. Please try again shortly.</p>
          )}
          {state.status === "done" && state.items.length === 0 && (
            <p className={styles.note}>No styles match “{term}”. Try a different word.</p>
          )}
          {state.status === "done" && state.items.length > 0 && (
            <>
              <p className={styles.heading}>Products</p>
              <ul className={styles.suggestions}>
                {state.items.map((item) => (
                  <li key={item.id}>
                    <Link href={`/products/${item.slug}`} className={styles.suggestion} onClick={onClose}>
                      <span className={styles.thumb}>
                        <ProductImage image={item.primary_image} name={item.name} seed={item.slug} sizes="64px" ratio="1 / 1" />
                      </span>
                      <span className={styles.suggestionText}>
                        <span className={styles.suggestionName}>{item.name}</span>
                        <Price price={item.price} fromPrice={item.from_price} priceVaries={item.price_varies} size="sm" showBadge={false} />
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
              <Link href={`/search?q=${encodeURIComponent(term)}`} className={styles.all} onClick={onClose}>
                See all {state.total} results
                <ArrowRight aria-hidden="true" size={18} />
              </Link>
            </>
          )}
        </div>
      </div>
    </Dialog>
  );
}
