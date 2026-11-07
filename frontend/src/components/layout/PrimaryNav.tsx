"use client";

import Link from "next/link";
import { ChevronDown } from "lucide-react";
import { type ReactNode, useEffect, useId, useRef, useState } from "react";

import type { LinkItem } from "@/lib/content/types";
import styles from "./SiteHeader.module.css";
import { useActiveNav } from "./useActiveNav";

/** The menu item that gets the collections dropdown (wherever an admin places it). */
const COLLECTIONS_HREF = "/collections";
const CLOSE_DELAY_MS = 140;

interface PrimaryNavProps {
  links: LinkItem[];
  /** Server-rendered collection links for the dropdown panel (streamed). */
  collectionsMenu?: ReactNode;
}

/** Desktop primary navigation: location-aware active state + an accessible collections menu. */
export function PrimaryNav({ links, collectionsMenu }: PrimaryNavProps) {
  const { active, onNavigate } = useActiveNav(links.map((link) => link.href));

  return (
    <ul className={styles.navList}>
      {links.map((link) => {
        const isActive = link.href === active;
        const anchor = (
          <Link
            href={link.href}
            className={styles.navLink}
            aria-current={isActive ? "page" : undefined}
            target={link.openInNewTab ? "_blank" : undefined}
            rel={link.openInNewTab ? "noopener noreferrer" : undefined}
            onClick={(event) => onNavigate(link.href, event)}
          >
            {link.label}
          </Link>
        );
        return (
          <li key={link.href} className={styles.navItem}>
            {link.href === COLLECTIONS_HREF && collectionsMenu ? (
              <Dropdown label={link.label} trigger={anchor}>
                {collectionsMenu}
              </Dropdown>
            ) : (
              anchor
            )}
          </li>
        );
      })}
    </ul>
  );
}

/**
 * Disclosure-style dropdown: the label stays a normal link; the chevron button toggles the
 * panel for keyboard and touch users, and pointer hover opens it with a short close delay.
 */
function Dropdown({ label, trigger, children }: { label: string; trigger: ReactNode; children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const panelId = useId();
  const rootRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const closeTimer = useRef<number | undefined>(undefined);

  const cancelClose = () => window.clearTimeout(closeTimer.current);
  const scheduleClose = () => {
    cancelClose();
    closeTimer.current = window.setTimeout(() => setOpen(false), CLOSE_DELAY_MS);
  };

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        buttonRef.current?.focus();
      }
    };
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  useEffect(() => cancelClose, []);

  return (
    <div
      ref={rootRef}
      className={styles.dropdown}
      data-open={open || undefined}
      onPointerEnter={(event) => {
        if (event.pointerType !== "mouse") return;
        cancelClose();
        setOpen(true);
      }}
      onPointerLeave={(event) => {
        if (event.pointerType === "mouse") scheduleClose();
      }}
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setOpen(false);
      }}
    >
      {trigger}
      <button
        ref={buttonRef}
        type="button"
        className={styles.dropdownToggle}
        aria-expanded={open}
        aria-controls={panelId}
        aria-label={`${open ? "Hide" : "Show"} ${label.toLowerCase()} menu`}
        onClick={() => setOpen((value) => !value)}
      >
        <ChevronDown aria-hidden="true" size={16} strokeWidth={2.2} />
      </button>
      {/* Clicking any link in the panel closes it. */}
      <div
        id={panelId}
        className={styles.panel}
        hidden={!open}
        onClick={(event) => {
          if ((event.target as HTMLElement).closest("a")) setOpen(false);
        }}
      >
        {children}
      </div>
    </div>
  );
}
