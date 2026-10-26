"use client";

import { type ReactNode, useEffect, useRef, useState } from "react";

type RevealState = "static" | "armed" | "in";

/**
 * Plays CSS entrance animations once, the first time the block scrolls into view.
 * Exposes `data-reveal-state` for the stylesheet: "static" (server render, no JS, or
 * reduced motion — content simply visible), "armed" (waiting, hidden) and "in" (playing).
 */
export function RevealOnView({ className, children }: { className?: string; children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  const [state, setState] = useState<RevealState>("static");

  useEffect(() => {
    const node = ref.current;
    if (!node || typeof IntersectionObserver === "undefined") return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setState("in");
          observer.disconnect();
        }
      },
      { threshold: 0.25 },
    );
    setState("armed");
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  return (
    <div ref={ref} className={className} data-reveal-state={state}>
      {children}
    </div>
  );
}
