"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  ExternalLink,
  FileText,
  FolderTree,
  Image as ImageIcon,
  LayoutDashboard,
  LayoutTemplate,
  LogOut,
  Menu,
  Navigation,
  Ruler,
  Settings,
  Shirt,
  Sparkles,
  Truck,
  Layers,
  type LucideIcon,
  MessageCircle,
  Receipt,
  BarChart3,
  Boxes,
  History,
  Star,
  TicketPercent,
  Undo2,
  Users,
} from "lucide-react";
import { type ReactNode, useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { EmptyState } from "@/components/ui/Feedback";
import { AdminSessionProvider, type Permission, useAdminSession } from "@/lib/admin/session";
import { LoadingState, adminStyles as styles } from "./Kit";

interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  permission: Permission;
}

const NAV: { heading: string; items: NavItem[] }[] = [
  {
    heading: "Overview",
    items: [{ href: "/admin", label: "Dashboard", icon: LayoutDashboard, permission: "admin:access" }],
  },
  {
    heading: "Sales",
    items: [
      { href: "/admin/orders", label: "Orders", icon: Receipt, permission: "orders:manage" },
      { href: "/admin/whatsapp", label: "WhatsApp requests", icon: MessageCircle, permission: "orders:manage" },
      { href: "/admin/requests", label: "Cancellations & returns", icon: Undo2, permission: "orders:manage" },
      { href: "/admin/coupons", label: "Coupons", icon: TicketPercent, permission: "settings:manage" },
      { href: "/admin/analytics", label: "Analytics", icon: BarChart3, permission: "orders:manage" },
    ],
  },
  {
    heading: "Catalogue",
    items: [
      { href: "/admin/products", label: "Products", icon: Shirt, permission: "catalog:manage" },
      { href: "/admin/categories", label: "Categories", icon: FolderTree, permission: "catalog:manage" },
      { href: "/admin/collections", label: "Collections", icon: Layers, permission: "content:manage" },
      { href: "/admin/size-charts", label: "Size charts", icon: Ruler, permission: "catalog:manage" },
      { href: "/admin/inventory", label: "Inventory", icon: Boxes, permission: "inventory:manage" },
      { href: "/admin/media", label: "Media library", icon: ImageIcon, permission: "media:manage" },
      { href: "/admin/reviews", label: "Reviews", icon: Star, permission: "content:manage" },
    ],
  },
  {
    heading: "Storefront",
    items: [
      { href: "/admin/homepage", label: "Homepage builder", icon: LayoutTemplate, permission: "content:manage" },
      { href: "/admin/navigation", label: "Navigation", icon: Navigation, permission: "content:manage" },
      { href: "/admin/pages", label: "Pages & FAQs", icon: FileText, permission: "content:manage" },
    ],
  },
  {
    heading: "Store",
    items: [
      { href: "/admin/settings", label: "Settings & theme", icon: Settings, permission: "settings:manage" },
      { href: "/admin/shipping", label: "Shipping & order policy", icon: Truck, permission: "settings:manage" },
      { href: "/admin/staff", label: "Staff & roles", icon: Users, permission: "users:manage" },
      { href: "/admin/activity", label: "Activity log", icon: History, permission: "audit:read" },
    ],
  },
];

function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  const { can } = useAdminSession();
  const pathname = usePathname();
  return (
    <>
      {NAV.map((group) => {
        const items = group.items.filter((i) => can(i.permission));
        if (items.length === 0) return null;
        return (
          <nav key={group.heading} className={styles.navGroup} aria-label={group.heading}>
            <p className={styles.navHeading}>{group.heading}</p>
            {items.map((item) => {
              const active = item.href === "/admin" ? pathname === "/admin" : pathname.startsWith(item.href);
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`${styles.navLink} ${active ? styles.navActive : ""}`}
                  aria-current={active ? "page" : undefined}
                  onClick={onNavigate}
                >
                  <Icon size={18} aria-hidden="true" />
                  {item.label}
                </Link>
              );
            })}
          </nav>
        );
      })}
    </>
  );
}

function UserMenu() {
  const { user, signOut } = useAdminSession();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent | KeyboardEvent) => {
      if (e instanceof KeyboardEvent ? e.key === "Escape" : !ref.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", close);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", close);
    };
  }, [open]);

  return (
    <div className={styles.userMenu} ref={ref}>
      <button type="button" className={styles.userButton} onClick={() => setOpen((o) => !o)} aria-expanded={open} aria-haspopup="menu">
        <span className={styles.avatar} aria-hidden="true">
          {(user.full_name || user.email).charAt(0).toUpperCase()}
        </span>
        <span>{user.full_name || user.email}</span>
      </button>
      {open && (
        <div className={styles.userPopover} role="menu">
          <div className={styles.userMeta}>
            <strong>{user.email}</strong>
            <br />
            {user.roles.join(", ")}
          </div>
          <Link href="/" className={styles.menuItem} role="menuitem" target="_blank">
            <ExternalLink size={16} aria-hidden="true" /> View storefront
          </Link>
          <button type="button" className={styles.menuItem} role="menuitem" onClick={() => void signOut()}>
            <LogOut size={16} aria-hidden="true" /> Sign out
          </button>
        </div>
      )}
    </div>
  );
}

function Shell({ children }: { children: ReactNode }) {
  const [menuOpen, setMenuOpen] = useState(false);
  return (
    <div className={styles.shell}>
      <aside className={styles.sidebar}>
        <div className={styles.brandRow}>
          <Sparkles size={18} aria-hidden="true" /> Twinkle Kids
          <span className={styles.brandTag}>Admin</span>
        </div>
        <NavLinks />
      </aside>
      <div className={styles.main}>
        <div className={styles.topbar}>
          <button type="button" className={styles.menuButton} onClick={() => setMenuOpen(true)} aria-label="Open navigation">
            <Menu size={22} aria-hidden="true" />
          </button>
          <span className={styles.topbarSpacer} />
          <UserMenu />
        </div>
        <div className={styles.content}>{children}</div>
      </div>
      <Dialog open={menuOpen} onClose={() => setMenuOpen(false)} title="Admin navigation" variant="drawer-start">
        <div className={styles.mobileNav}>
          <NavLinks onNavigate={() => setMenuOpen(false)} />
        </div>
      </Dialog>
    </div>
  );
}

export function AdminShell({ children }: { children: ReactNode }) {
  return (
    <AdminSessionProvider
      renderState={(state, signOut) =>
        state === "loading" ? (
          <LoadingState label="Checking your session…" />
        ) : (
          <div className={styles.center}>
            <EmptyState
              tone="error"
              title={state === "forbidden" ? "No admin access" : "Admin is unavailable"}
              description={
                state === "forbidden"
                  ? "This account is signed in but does not have staff permissions."
                  : `The admin API could not be reached (${state.error}).`
              }
              action={
                <Button variant="outline" onClick={() => void signOut()}>
                  Sign out
                </Button>
              }
            />
          </div>
        )
      }
    >
      <Shell>{children}</Shell>
    </AdminSessionProvider>
  );
}
