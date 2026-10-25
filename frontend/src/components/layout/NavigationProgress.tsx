"use client";

import { usePathname, useSearchParams } from "next/navigation";
import { createContext, type ReactNode, Suspense, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";

import styles from "./NavigationProgress.module.css";

/**
 * Thin brand-coloured bar at the top of the window while a client-side navigation is genuinely
 * in flight: from a same-site link click (or `start()` before `router.push`) until the URL
 * commits. It is indeterminate — no invented percentages — appears only after a short delay so
 * prefetched, instant navigations never flicker, and gives up after a timeout if a navigation
 * is cancelled, so it can never spin forever.
 */

const SHOW_DELAY_MS = 150;
const GIVE_UP_MS = 12_000;

interface NavigationProgressApi {
  /** Call right before a programmatic navigation (router.push / replace) to `href`. */
  start: (href?: string) => void;
}

const ProgressContext = createContext<NavigationProgressApi>({ start: () => {} });

export function useNavigationProgress(): NavigationProgressApi {
  return useContext(ProgressContext);
}

function currentUrl(): string {
  return `${window.location.pathname}${window.location.search}`;
}

export function NavigationProgressProvider({ children }: { children: ReactNode }) {
  const [active, setActive] = useState(false);
  const [visible, setVisible] = useState(false);
  const timers = useRef<{ show?: number; giveUp?: number }>({});

  const clear = () => {
    window.clearTimeout(timers.current.show);
    window.clearTimeout(timers.current.giveUp);
  };

  const done = useCallback(() => {
    clear();
    setActive(false);
    setVisible(false);
  }, []);

  const start = useCallback((href?: string) => {
    if (href !== undefined) {
      const target = new URL(href, window.location.href);
      if (`${target.pathname}${target.search}` === currentUrl()) return; // nothing will change
    }
    clear();
    setActive(true);
    timers.current.show = window.setTimeout(() => setVisible(true), SHOW_DELAY_MS);
    timers.current.giveUp = window.setTimeout(done, GIVE_UP_MS);
  }, [done]);

  // Same-site link clicks (covers every <Link> without wiring each one). Capture phase: <Link>
  // itself calls preventDefault to navigate client-side, so a bubbling listener would miss it.
  useEffect(() => {
    function onClick(event: MouseEvent) {
      if (event.button !== 0) return;
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      const anchor = (event.target as Element | null)?.closest?.("a");
      if (!anchor || !anchor.href || anchor.target === "_blank" || anchor.hasAttribute("download")) return;
      const url = new URL(anchor.href, window.location.href);
      if (url.origin !== window.location.origin) return;
      if (`${url.pathname}${url.search}` === currentUrl()) return; // same page or hash jump
      start();
    }
    document.addEventListener("click", onClick, true);
    return () => {
      document.removeEventListener("click", onClick, true);
      clear();
    };
  }, [start]);

  const api = useMemo(() => ({ start }), [start]);

  return (
    <ProgressContext.Provider value={api}>
      {children}
      <Suspense fallback={null}>
        <CompletionWatcher active={active} onDone={done} />
      </Suspense>
      <div className={`${styles.progress} ${visible ? styles.visible : ""}`} aria-hidden="true">
        <span className={styles.bar} />
      </div>
      <p className="visually-hidden" role="status" aria-live="polite">
        {visible ? "Loading page" : ""}
      </p>
    </ProgressContext.Provider>
  );
}

/** Finishes the bar once the new URL has committed. */
function CompletionWatcher({ active, onDone }: { active: boolean; onDone: () => void }) {
  const pathname = usePathname();
  const search = useSearchParams().toString();
  const first = useRef(true);
  useEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    if (active) onDone();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- react to URL changes only
  }, [pathname, search]);
  return null;
}
