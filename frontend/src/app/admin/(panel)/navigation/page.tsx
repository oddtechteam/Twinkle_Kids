"use client";

import { Pencil, Plus, Trash2 } from "lucide-react";
import { type FormEvent, useState } from "react";

import {
  AdminPage,
  ConfirmDialog,
  ErrorState,
  LoadingState,
  Pill,
  SelectInput,
  SortableList,
  TextInput,
  Toggle,
  adminStyles as styles,
} from "@/components/admin/Kit";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { useToast } from "@/components/ui/Toast";
import { adminApi, refreshStorefront } from "@/lib/admin/api";
import { useMutation, useResource } from "@/lib/admin/hooks";
import type { LinkType, NavigationItem, NavigationMenu } from "@/lib/admin/types";

const MENUS: { id: NavigationMenu; label: string; hint: string }[] = [
  { id: "header", label: "Header", hint: "Main menu on desktop. Child items appear in a dropdown." },
  { id: "footer", label: "Footer", hint: "Use “Heading” items as column titles with links underneath. Top-level links appear as policy links." },
  { id: "mobile", label: "Mobile", hint: "Menu shown in the mobile drawer. Leave empty to reuse the header menu." },
];

const LINK_TYPES: { value: LinkType; label: string }[] = [
  { value: "category", label: "Category" },
  { value: "collection", label: "Collection" },
  { value: "page", label: "Website page" },
  { value: "url", label: "Custom link" },
  { value: "heading", label: "Heading (no link)" },
];

interface ItemForm {
  label: string;
  link_type: LinkType;
  parent_id: string;
  target: string;
  url: string;
  is_active: boolean;
  open_in_new_tab: boolean;
}

function toForm(item?: NavigationItem): ItemForm {
  return {
    label: item?.label ?? "",
    link_type: item?.link_type ?? "category",
    parent_id: item?.parent_id ?? "",
    target: item?.category_id ?? item?.collection_id ?? item?.page_id ?? "",
    url: item?.url ?? "",
    is_active: item?.is_active ?? true,
    open_in_new_tab: item?.open_in_new_tab ?? false,
  };
}

function ItemDialog({
  menu,
  item,
  topLevel,
  isParent,
  onClose,
  onSaved,
}: {
  menu: NavigationMenu;
  item: NavigationItem | null;
  topLevel: NavigationItem[];
  isParent: boolean;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [f, setF] = useState(() => toForm(item ?? undefined));
  const { run, pending } = useMutation();
  const categories = useResource(adminApi.categories, "nav-categories");
  const collections = useResource(adminApi.collections, "nav-collections");
  const pages = useResource(adminApi.pages, "nav-pages");
  const set = <K extends keyof ItemForm>(key: K, value: ItemForm[K]) => setF((s) => ({ ...s, [key]: value }));

  const targets =
    f.link_type === "category"
      ? (categories.data ?? []).map((c) => ({ value: c.id, label: c.is_active ? c.name : `${c.name} (hidden)` }))
      : f.link_type === "collection"
        ? (collections.data ?? []).map((c) => ({ value: c.id, label: c.status === "published" ? c.name : `${c.name} (draft)` }))
        : (pages.data ?? []).map((p) => ({ value: p.id, label: p.status === "published" ? p.title : `${p.title} (draft)` }));

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const body = {
      menu,
      label: f.label.trim(),
      link_type: f.link_type,
      parent_id: f.parent_id || null,
      category_id: f.link_type === "category" ? f.target || null : null,
      collection_id: f.link_type === "collection" ? f.target || null : null,
      page_id: f.link_type === "page" ? f.target || null : null,
      url: f.link_type === "url" ? f.url.trim() || null : null,
      is_active: f.is_active,
      open_in_new_tab: f.link_type === "url" && f.open_in_new_tab,
    };
    const res = await run(() => (item ? adminApi.updateNavigation(item.id, body) : adminApi.createNavigation(body)), {
      success: item ? "Menu item saved" : "Menu item added",
    });
    if (res.ok) onSaved();
  };

  // Only top-level, non-self items can be parents (menus have two levels).
  const parents = topLevel.filter((p) => p.id !== item?.id).map((p) => ({ value: p.id, label: p.label }));

  return (
    <Dialog open onClose={onClose} title={item ? "Edit menu item" : "Add menu item"}>
      <form onSubmit={submit} className={styles.stack} noValidate>
        <TextInput label="Label" value={f.label} onChange={(v) => set("label", v)} maxLength={80} required />
        <SelectInput label="Links to" value={f.link_type} onChange={(v) => setF((s) => ({ ...s, link_type: v as LinkType, target: "" }))} options={LINK_TYPES} />
        {(f.link_type === "category" || f.link_type === "collection" || f.link_type === "page") && (
          <SelectInput label="Destination" value={f.target} onChange={(v) => set("target", v)} placeholder="Choose…" options={targets} />
        )}
        {f.link_type === "url" && (
          <>
            <TextInput label="URL" placeholder="/sale or https://…" hint="Site-relative paths or https:// links only." value={f.url} onChange={(v) => set("url", v)} maxLength={500} />
            <Toggle label="Open in a new tab" checked={f.open_in_new_tab} onChange={(v) => set("open_in_new_tab", v)} />
          </>
        )}
        {isParent ? (
          <p className={styles.hint}>This item has child links, so it stays at the top level.</p>
        ) : (
          <SelectInput label="Parent" value={f.parent_id} onChange={(v) => set("parent_id", v)} placeholder="None (top level)" options={parents} />
        )}
        <Toggle label="Active" checked={f.is_active} onChange={(v) => set("is_active", v)} />
        <Button type="submit" loading={pending} disabled={!f.label.trim()}>
          {item ? "Save item" : "Add item"}
        </Button>
      </form>
    </Dialog>
  );
}

export default function NavigationPage() {
  const toast = useToast();
  const [menu, setMenu] = useState<NavigationMenu>("header");
  const items = useResource(() => adminApi.navigation(menu), menu);
  const { run, pending } = useMutation();
  const [editing, setEditing] = useState<NavigationItem | null | "new">(null);
  const [deleting, setDeleting] = useState<NavigationItem | null>(null);

  const all = items.data ?? [];
  const topLevel = all.filter((i) => !i.parent_id).sort((a, b) => a.position - b.position);
  const childrenOf = (id: string) => all.filter((i) => i.parent_id === id).sort((a, b) => a.position - b.position);

  const changed = async () => {
    await items.reload();
    if (!(await refreshStorefront())) {
      toast.show({ tone: "warning", title: "Saved, but the storefront cache wasn't refreshed", description: "Changes appear within a few minutes." });
    }
  };

  const reorder = async (next: NavigationItem[]) => {
    const ids = next.map((i) => i.id);
    items.setData((prev) =>
      prev?.map((i) => (ids.includes(i.id) ? { ...i, position: ids.indexOf(i.id) } : i)),
    );
    const res = await run(() => adminApi.reorderNavigation(ids), { success: "Menu order saved" });
    if (res.ok) void changed();
    else void items.reload();
  };

  const row = (item: NavigationItem) => (
    <span className={styles.cellTitle}>
      <strong>{item.label}</strong>
      <span className={styles.hint}>
        {LINK_TYPES.find((t) => t.value === item.link_type)?.label}
        {item.url ? ` · ${item.url}` : ""}
      </span>
      {!item.is_active && <Pill tone="grey">Hidden</Pill>}
    </span>
  );

  const actions = (item: NavigationItem) => (
    <>
      <button type="button" className={styles.iconButton} onClick={() => setEditing(item)} aria-label={`Edit ${item.label}`}>
        <Pencil size={15} aria-hidden="true" />
      </button>
      <button type="button" className={`${styles.iconButton} ${styles.dangerIcon}`} onClick={() => setDeleting(item)} aria-label={`Delete ${item.label}`}>
        <Trash2 size={15} aria-hidden="true" />
      </button>
    </>
  );

  const current = MENUS.find((m) => m.id === menu);

  return (
    <AdminPage
      title="Navigation"
      description="Menu changes go live immediately."
      breadcrumbs={[{ label: "Navigation" }]}
      actions={
        <Button iconStart={<Plus aria-hidden="true" />} onClick={() => setEditing("new")}>
          Add item
        </Button>
      }
    >
      <div className={styles.tabs} role="tablist" aria-label="Menus">
        {MENUS.map((m) => (
          <button key={m.id} type="button" role="tab" className={styles.tab} aria-selected={menu === m.id} onClick={() => setMenu(m.id)}>
            {m.label}
          </button>
        ))}
      </div>
      <div className={styles.stack} role="tabpanel">
        <p className={styles.hint}>{current?.hint}</p>
        {items.error && <ErrorState message={items.error} onRetry={items.reload} />}
        {items.loading && !items.data && <LoadingState />}
        {items.data && topLevel.length === 0 && <p className={styles.hint}>This menu is empty.</p>}
        {topLevel.length > 0 && (
          <SortableList
            label={`${current?.label} menu`}
            items={topLevel}
            getId={(i) => i.id}
            onReorder={(next) => void reorder(next)}
            renderItem={(item) => {
              const kids = childrenOf(item.id);
              return (
                <div className={styles.stack} style={{ gap: "var(--space-2)" }}>
                  {row(item)}
                  {kids.length > 0 && (
                    <SortableList label={`${item.label} links`} items={kids} getId={(i) => i.id} onReorder={(next) => void reorder(next)} renderItem={row} renderActions={actions} />
                  )}
                </div>
              );
            }}
            renderActions={actions}
          />
        )}
      </div>

      {editing !== null && (
        <ItemDialog
          key={editing === "new" ? `new-${menu}` : editing.id}
          menu={menu}
          item={editing === "new" ? null : editing}
          topLevel={topLevel}
          isParent={editing !== "new" && childrenOf(editing.id).length > 0}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            void changed();
          }}
        />
      )}
      <ConfirmDialog
        open={deleting !== null}
        title={`Delete “${deleting?.label ?? ""}”?`}
        message={deleting && childrenOf(deleting.id).length > 0 ? "Its child links are deleted too." : "The item is removed from the menu."}
        confirmLabel="Delete"
        destructive
        pending={pending}
        onClose={() => setDeleting(null)}
        onConfirm={async () => {
          if (!deleting) return;
          const res = await run(() => adminApi.deleteNavigation(deleting.id), { success: "Menu item deleted" });
          setDeleting(null);
          if (res.ok) void changed();
        }}
      />
    </AdminPage>
  );
}
