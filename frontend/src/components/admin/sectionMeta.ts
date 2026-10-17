import type { SectionType, SelectionMode } from "@/lib/admin/types";

/** Admin-side description of each homepage section type (mirrors backend content_settings.py). */
export interface SectionMeta {
  label: string;
  description: string;
  /** Section shows products and needs a selection mode. */
  products: boolean;
  /** Section can show a desktop/mobile image. */
  media: boolean;
  defaultMode: SelectionMode;
  /** Starting settings; every required field is left for the editor to fill in. */
  defaults: () => Record<string, unknown>;
}

export const SECTION_META: Record<SectionType, SectionMeta> = {
  hero_banner: {
    label: "Hero banner",
    description: "Large headline with image and up to two buttons.",
    products: false,
    media: true,
    defaultMode: "none",
    defaults: () => ({ headline: { lead: "", highlight: "", trail: "" }, theme: "blush", layout: "image-right", trust: [] }),
  },
  category_grid: {
    label: "Category grid",
    description: "Tiles linking to categories.",
    products: false,
    media: false,
    defaultMode: "none",
    defaults: () => ({ category_ids: [], layout: "bento", show_view_all: true }),
  },
  product_carousel: {
    label: "Product carousel",
    description: "A scrollable row of products.",
    products: true,
    media: false,
    defaultMode: "newest",
    defaults: () => ({ theme: "ivory", columns_desktop: 4 }),
  },
  product_grid: {
    label: "Product grid",
    description: "A grid of products.",
    products: true,
    media: false,
    defaultMode: "newest",
    defaults: () => ({ theme: "ivory", columns_desktop: 4 }),
  },
  editorial_banner: {
    label: "Editorial banner",
    description: "Image with a short story and a button.",
    products: false,
    media: true,
    defaultMode: "none",
    defaults: () => ({ theme: "navy", image_position: "right" }),
  },
  promo_banner: {
    label: "Promotional banner",
    description: "Highlight an offer or new arrival with an image.",
    products: false,
    media: true,
    defaultMode: "none",
    defaults: () => ({ theme: "blush", image_position: "right" }),
  },
  collection_showcase: {
    label: "Collection showcase",
    description: "Tiles linking to selected collections.",
    products: false,
    media: false,
    defaultMode: "none",
    defaults: () => ({ collection_ids: [], layout: "tiles" }),
  },
  occasion_collection: {
    label: "Occasion spotlight",
    description: "Feature one collection (e.g. birthdays, festive) with its products.",
    products: true,
    media: true,
    defaultMode: "collection",
    defaults: () => ({ theme: "blush" }),
  },
  trust_strip: {
    label: "Trust strip",
    description: "Short reassurance points (fabric, sizing help, support).",
    products: false,
    media: false,
    defaultMode: "none",
    defaults: () => ({ items: [] }),
  },
  testimonials: {
    label: "Testimonials",
    description: "Genuine customer reviews only.",
    products: false,
    media: false,
    defaultMode: "none",
    defaults: () => ({ items: [] }),
  },
  faq: {
    label: "FAQ",
    description: "Questions and answers.",
    products: false,
    media: false,
    defaultMode: "none",
    defaults: () => ({ items: [] }),
  },
  announcement: {
    label: "Announcement strip",
    description: "A one-line message inside the page.",
    products: false,
    media: false,
    defaultMode: "none",
    defaults: () => ({ message: "", theme: "navy" }),
  },
  contact: {
    label: "Contact",
    description: "WhatsApp, phone and email from store settings.",
    products: false,
    media: false,
    defaultMode: "none",
    defaults: () => ({ show_whatsapp: true, show_phone: true, show_email: true }),
  },
  rich_text: {
    label: "Text block",
    description: "A plain-text paragraph (no HTML).",
    products: false,
    media: false,
    defaultMode: "none",
    defaults: () => ({ body: "", alignment: "center" }),
  },
};

export const SECTION_TYPES = Object.keys(SECTION_META) as SectionType[];

export const THEME_OPTIONS = [
  { value: "ivory", label: "Ivory" },
  { value: "blush", label: "Blush" },
  { value: "navy", label: "Navy" },
  { value: "gold", label: "Gold" },
];

export const ICON_OPTIONS = ["sparkles", "ruler", "message-circle", "gift", "heart", "shield-check", "shirt", "star"].map((v) => ({
  value: v,
  label: v,
}));

const CTA_KEYS = new Set(["cta", "primary_cta", "secondary_cta", "link"]);

/** Drop half-filled optional buttons so the backend's strict schema accepts the settings. */
export function cleanSettings(settings: Record<string, unknown>): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(settings)) {
    if (CTA_KEYS.has(key)) {
      const cta = value as { label?: string; href?: string } | null | undefined;
      if (cta && cta.label?.trim()) out[key] = { label: cta.label.trim(), href: cta.href?.trim() || "/" };
      continue;
    }
    out[key] = value;
  }
  return out;
}
