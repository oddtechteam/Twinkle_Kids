"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { useCallback, useEffect, useId, useRef, useState } from "react";

import type { CardProduct } from "@/lib/catalog/adapters";
import { ProductCard } from "./ProductCard";
import styles from "./ProductRail.module.css";

/** Horizontally scrolling product carousel (native scroll-snap; arrows on wider screens). */
export function ProductRail({ products, label }: { products: CardProduct[]; label: string }) {
  const track = useRef<HTMLUListElement>(null);
  const [edges, setEdges] = useState({ start: true, end: false });
  const id = useId();

  const measure = useCallback(() => {
    const el = track.current;
    if (!el) return;
    setEdges({
      start: el.scrollLeft <= 4,
      end: el.scrollLeft + el.clientWidth >= el.scrollWidth - 4,
    });
  }, []);

  useEffect(() => {
    measure();
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, [measure]);

  const scroll = (direction: 1 | -1) => {
    const el = track.current;
    if (!el) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    el.scrollBy({ left: direction * el.clientWidth * 0.85, behavior: reduce ? "auto" : "smooth" });
  };

  return (
    <div className={styles.rail}>
      <ul
        ref={track}
        id={id}
        className={styles.track}
        onScroll={measure}
        aria-label={label}
        tabIndex={0}
      >
        {products.map((product, index) => (
          <li key={product.slug} className={styles.slide}>
            <ProductCard product={product} priority={index < 2} sizes="(min-width: 1100px) 22vw, (min-width: 700px) 32vw, 64vw" />
          </li>
        ))}
      </ul>
      <div className={styles.controls}>
        <button
          type="button"
          className={styles.arrow}
          onClick={() => scroll(-1)}
          disabled={edges.start}
          aria-controls={id}
          aria-label="Scroll to previous products"
        >
          <ChevronLeft aria-hidden="true" size={22} />
        </button>
        <button
          type="button"
          className={styles.arrow}
          onClick={() => scroll(1)}
          disabled={edges.end}
          aria-controls={id}
          aria-label="Scroll to more products"
        >
          <ChevronRight aria-hidden="true" size={22} />
        </button>
      </div>
    </div>
  );
}
