"use client";

import { Plus, Trash2 } from "lucide-react";
import { type ReactNode, useState } from "react";

import {
  AdminPage,
  Card,
  ErrorState,
  Field,
  LoadingState,
  SelectInput,
  TextArea,
  TextInput,
  Toggle,
  adminStyles as styles,
} from "@/components/admin/Kit";
import { MediaField } from "@/components/admin/Pickers";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { adminApi, refreshStorefront } from "@/lib/admin/api";
import { useMutation, useResource } from "@/lib/admin/hooks";
import type { PaymentOption, StoreSettings } from "@/lib/admin/types";
import { SORT_OPTIONS } from "@/lib/catalog/query";

const TABS = [
  { id: "store", label: "Store" },
  { id: "theme", label: "Theme" },
  { id: "announcement", label: "Announcement" },
  { id: "contact", label: "Contact & social" },
  { id: "checkout", label: "Checkout" },
  { id: "seo", label: "SEO" },
] as const;
type Tab = (typeof TABS)[number]["id"];

const COLOURS: { key: string; label: string; fallback: string }[] = [
  { key: "navy", label: "Navy (text & primary buttons)", fallback: "#1c2d52" },
  { key: "ivory", label: "Ivory (page background)", fallback: "#fff7f1" },
  { key: "blush", label: "Blush (soft highlights)", fallback: "#f5cdd3" },
  { key: "coral", label: "Coral (accent)", fallback: "#ee788b" },
  { key: "gold", label: "Gold (details)", fallback: "#d6b17b" },
];

const PAYMENT_METHODS = [
  { value: "cash_on_delivery", label: "Cash on delivery" },
  { value: "upi_manual", label: "UPI (manual confirmation)" },
  { value: "bank_transfer", label: "Bank transfer" },
  { value: "other", label: "Other" },
];

const HEX = /^#[0-9a-fA-F]{6}$/;
const orNull = (v: string | null | undefined) => (v && v.trim() ? v.trim() : null);

function SaveBar({ pending, onSave }: { pending: boolean; onSave: () => void }) {
  return (
    <div>
      <Button loading={pending} onClick={onSave}>
        Save changes
      </Button>
    </div>
  );
}

export default function SettingsPage() {
  const settings = useResource(adminApi.settings, "settings");
  if (settings.loading && !settings.data) return <LoadingState />;
  if (settings.error && !settings.data) return <ErrorState message={settings.error} onRetry={settings.reload} />;
  if (!settings.data) return null;
  return <SettingsEditor initial={settings.data} onSaved={settings.setData} />;
}

function SettingsEditor({ initial, onSaved }: { initial: StoreSettings; onSaved: (s: StoreSettings) => void }) {
  const toast = useToast();
  const [tab, setTab] = useState<Tab>("store");
  const [s, setS] = useState(initial);
  const { run, pending } = useMutation();
  const set = <K extends keyof StoreSettings>(key: K, value: StoreSettings[K]) => setS((prev) => ({ ...prev, [key]: value }));

  const save = async (changes: Partial<StoreSettings>) => {
    const res = await run(() => adminApi.updateSettings(changes), { success: "Settings saved" });
    if (!res.ok) return;
    onSaved(res.result);
    if (!(await refreshStorefront())) {
      toast.show({ tone: "warning", title: "Saved, but the storefront cache wasn't refreshed", description: "Changes appear within a few minutes." });
    }
  };

  let body: ReactNode;
  switch (tab) {
    case "store":
      body = (
        <Card title="Store">
          <div className={styles.grid2}>
            <TextInput label="Store name" value={s.store_name} onChange={(v) => set("store_name", v)} maxLength={120} required />
            <TextInput label="Tagline" value={s.tagline ?? ""} onChange={(v) => set("tagline", v)} maxLength={200} />
          </div>
          <div className={styles.grid2}>
            <MediaField label="Logo" hint="Shown in the header and footer. Leave empty for the text logo." value={s.logo_media_id} onChange={(id) => set("logo_media_id", id)} purpose="content_image" />
            <MediaField label="Favicon" hint="Square PNG, at least 64×64." value={s.favicon_media_id} onChange={(id) => set("favicon_media_id", id)} purpose="content_image" />
          </div>
          <div className={styles.grid2}>
            <SelectInput label="Default product sort" value={s.default_product_sort} onChange={(v) => set("default_product_sort", v)} options={SORT_OPTIONS} />
            <TextInput
              label="Default low-stock threshold"
              type="number"
              min={0}
              value={String(s.default_low_stock_threshold)}
              onChange={(v) => set("default_low_stock_threshold", Number.parseInt(v || "0", 10))}
            />
          </div>
          <p className={styles.hint}>Currency: {s.currency_code} (fixed).</p>
          <SaveBar
            pending={pending}
            onSave={() =>
              void save({
                store_name: s.store_name,
                tagline: orNull(s.tagline),
                logo_media_id: s.logo_media_id,
                favicon_media_id: s.favicon_media_id,
                default_product_sort: s.default_product_sort,
                default_low_stock_threshold: s.default_low_stock_threshold,
              })
            }
          />
        </Card>
      );
      break;
    case "theme": {
      const invalid = COLOURS.filter((c) => s.theme[c.key] && !HEX.test(s.theme[c.key] ?? ""));
      body = (
        <Card title="Brand colours" hint="Leave a colour on “Default” to keep the Twinkle Kids palette. Only #RRGGBB values are accepted.">
          {COLOURS.map((c) => {
            const value = s.theme[c.key] ?? "";
            return (
              <Field key={c.key} label={c.label} error={value && !HEX.test(value) ? "Use #RRGGBB" : null}>
                {(id) => (
                  <div className={styles.colourRow}>
                    <input
                      type="color"
                      className={styles.colourInput}
                      value={HEX.test(value) ? value : c.fallback}
                      onChange={(e) => set("theme", { ...s.theme, [c.key]: e.target.value })}
                      aria-label={`${c.label} picker`}
                    />
                    <input id={id} className={styles.input} style={{ maxWidth: "9rem" }} value={value} placeholder={c.fallback} onChange={(e) => set("theme", { ...s.theme, [c.key]: e.target.value.trim() })} />
                    {value && (
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => {
                          const next = { ...s.theme };
                          delete next[c.key];
                          set("theme", next);
                        }}
                      >
                        Default
                      </Button>
                    )}
                  </div>
                )}
              </Field>
            );
          })}
          <Button
            disabled={invalid.length > 0}
            loading={pending}
            onClick={() => void save({ theme: Object.fromEntries(Object.entries(s.theme).filter(([, v]) => v)) })}
          >
            Save colours
          </Button>
        </Card>
      );
      break;
    }
    case "announcement": {
      const a = s.announcement;
      body = (
        <Card title="Announcement bar" hint="The strip at the very top of every storefront page.">
          <Toggle label="Show the announcement bar" checked={Boolean(a.enabled)} onChange={(v) => set("announcement", { ...a, enabled: v })} />
          <TextInput label="Message" value={a.message ?? ""} onChange={(v) => set("announcement", { ...a, message: v })} maxLength={140} />
          <div className={styles.grid2}>
            <TextInput label="Link text" value={a.link_label ?? ""} onChange={(v) => set("announcement", { ...a, link_label: v })} maxLength={40} />
            <TextInput label="Link" placeholder="/shop or https://…" value={a.link_href ?? ""} onChange={(v) => set("announcement", { ...a, link_href: v })} maxLength={500} />
          </div>
          <SaveBar
            pending={pending}
            onSave={() =>
              void save({
                announcement: {
                  enabled: Boolean(a.enabled),
                  message: a.message ?? "",
                  link_label: a.link_label ?? "",
                  link_href: orNull(a.link_href),
                },
              })
            }
          />
        </Card>
      );
      break;
    }
    case "contact":
      body = (
        <Card title="Contact & social" hint="Empty details are hidden on the storefront.">
          <div className={styles.grid2}>
            <TextInput label="Email" type="email" value={s.contact_email ?? ""} onChange={(v) => set("contact_email", v)} maxLength={254} />
            <TextInput label="Phone" value={s.contact_phone ?? ""} onChange={(v) => set("contact_phone", v)} maxLength={20} placeholder="+91 98765 43210" />
          </div>
          <TextArea label="Business address" value={s.business_address ?? ""} onChange={(v) => set("business_address", v)} maxLength={500} rows={3} />
          <TextInput label="Business hours" value={s.business_hours ?? ""} onChange={(v) => set("business_hours", v)} maxLength={120} placeholder="Mon–Sat, 10am–7pm" />
          <div className={styles.grid2}>
            {(["instagram", "facebook", "youtube", "pinterest"] as const).map((key) => (
              <TextInput
                key={key}
                label={key.charAt(0).toUpperCase() + key.slice(1)}
                placeholder="https://…"
                value={s.social_links[key] ?? ""}
                onChange={(v) => set("social_links", { ...s.social_links, [key]: v })}
                maxLength={300}
              />
            ))}
          </div>
          <SaveBar
            pending={pending}
            onSave={() =>
              void save({
                contact_email: orNull(s.contact_email),
                contact_phone: orNull(s.contact_phone),
                business_address: orNull(s.business_address),
                business_hours: orNull(s.business_hours),
                social_links: Object.fromEntries(
                  (["instagram", "facebook", "youtube", "pinterest"] as const).map((k) => [k, orNull(s.social_links[k])]),
                ),
              })
            }
          />
        </Card>
      );
      break;
    case "checkout": {
      const options = s.payment_options;
      const setOption = (index: number, patch: Partial<PaymentOption>) =>
        set("payment_options", options.map((o, i) => (i === index ? { ...o, ...patch } : o)));
      const unused = PAYMENT_METHODS.filter((m) => !options.some((o) => o.method === m.value));
      body = (
        <div className={styles.stack}>
          <Card title="Checkout">
            <Toggle label="Allow guest checkout" checked={s.guest_checkout_enabled} onChange={(v) => set("guest_checkout_enabled", v)} />
          </Card>
          <Card
            title="WhatsApp ordering"
            hint="Customers can open WhatsApp with their bag pre-filled. Opening WhatsApp doesn't prove a message was sent — these stay as WhatsApp requests until you confirm an order."
          >
            <Toggle label="Enable “Order on WhatsApp”" checked={s.whatsapp_ordering_enabled} onChange={(v) => set("whatsapp_ordering_enabled", v)} />
            <TextInput label="WhatsApp number" hint="With country code, e.g. +91 98765 43210" value={s.whatsapp_number ?? ""} onChange={(v) => set("whatsapp_number", v)} maxLength={20} />
            <TextArea
              label="Message introduction"
              hint="Plain text placed before the bag details."
              value={s.whatsapp_message_template ?? ""}
              onChange={(v) => set("whatsapp_message_template", v)}
              maxLength={500}
              rows={3}
            />
          </Card>
          <Card
            title="Payment options"
            hint="Offline methods shown as instructions. There is no online payment; you record payments yourself when they arrive."
            actions={
              <Button
                size="sm"
                variant="soft"
                iconStart={<Plus aria-hidden="true" />}
                disabled={unused.length === 0}
                onClick={() => {
                  const method = unused[0];
                  if (method) set("payment_options", [...options, { method: method.value as PaymentOption["method"], enabled: true, label: method.label, instructions: "" }]);
                }}
              >
                Add method
              </Button>
            }
          >
            {options.length === 0 && <p className={styles.hint}>No payment methods listed.</p>}
            {options.map((o, index) => (
              <div key={o.method} className={styles.blockEditor}>
                <div className={styles.blockHeader}>
                  <Toggle label="Enabled" checked={o.enabled} onChange={(v) => setOption(index, { enabled: v })} />
                  <button type="button" className={`${styles.iconButton} ${styles.dangerIcon}`} onClick={() => set("payment_options", options.filter((_, i) => i !== index))} aria-label="Remove method">
                    <Trash2 size={15} aria-hidden="true" />
                  </button>
                </div>
                <div className={styles.grid2}>
                  <SelectInput
                    label="Method"
                    value={o.method}
                    onChange={(v) => setOption(index, { method: v as PaymentOption["method"] })}
                    options={PAYMENT_METHODS.filter((m) => m.value === o.method || !options.some((x) => x.method === m.value))}
                  />
                  <TextInput label="Label" value={o.label} onChange={(v) => setOption(index, { label: v })} maxLength={60} />
                </div>
                <TextArea label="Instructions" value={o.instructions} onChange={(v) => setOption(index, { instructions: v })} maxLength={300} rows={2} />
              </div>
            ))}
          </Card>
          <SaveBar
            pending={pending}
            onSave={() =>
              void save({
                guest_checkout_enabled: s.guest_checkout_enabled,
                whatsapp_ordering_enabled: s.whatsapp_ordering_enabled,
                whatsapp_number: orNull(s.whatsapp_number),
                whatsapp_message_template: orNull(s.whatsapp_message_template),
                payment_options: options,
              })
            }
          />
        </div>
      );
      break;
    }
    case "seo": {
      const seo = s.seo_defaults;
      body = (
        <Card title="Search & sharing defaults">
          <TextInput label="Title suffix" hint="Added after page titles, e.g. “ | Twinkle Kids”" value={seo.title_suffix ?? ""} onChange={(v) => set("seo_defaults", { ...seo, title_suffix: v })} maxLength={60} />
          <TextArea label="Default description" value={seo.default_description ?? ""} onChange={(v) => set("seo_defaults", { ...seo, default_description: v })} maxLength={320} rows={3} />
          <MediaField
            label="Default sharing image"
            hint="Used when a page has no image of its own (1200×630 recommended)."
            value={seo.og_image_media_id ?? null}
            onChange={(id) => set("seo_defaults", { ...seo, og_image_media_id: id })}
            purpose="content_image"
          />
          <SaveBar
            pending={pending}
            onSave={() =>
              void save({
                seo_defaults: {
                  title_suffix: seo.title_suffix ?? "",
                  default_description: seo.default_description ?? "",
                  og_image_media_id: seo.og_image_media_id ?? null,
                },
              })
            }
          />
        </Card>
      );
      break;
    }
  }

  return (
    <AdminPage title="Settings & theme" breadcrumbs={[{ label: "Settings" }]}>
      <div className={styles.tabs} role="tablist" aria-label="Settings sections">
        {TABS.map((t) => (
          <button key={t.id} type="button" role="tab" className={styles.tab} aria-selected={tab === t.id} onClick={() => setTab(t.id)}>
            {t.label}
          </button>
        ))}
      </div>
      <div role="tabpanel">{body}</div>
    </AdminPage>
  );
}
