/**
 * Maps the public CMS API (`/content/site`, `/content/homepage`) onto the storefront content
 * model. Only published data reaches these endpoints; drafts are never visible here.
 */

import type { Category, ProductImage, ProductSort, ProductSummary } from "@/lib/api/types";
import { type ImageFrame, framedImage } from "@/lib/media/frames";
import type {
  HomepageSection,
  IconName,
  LinkItem,
  MediaRef,
  SiteContent,
  Theme,
} from "./types";

// --- API shapes -------------------------------------------------------------------------------

interface PublicLink {
  label: string;
  href: string | null;
  open_in_new_tab: boolean;
  children: PublicLink[];
}

export interface PublicSite {
  store_name: string;
  tagline: string | null;
  logo: ProductImage | null;
  favicon: ProductImage | null;
  theme: Record<string, string>;
  announcement: { enabled?: boolean; message?: string; link_label?: string; link_href?: string };
  contact: { email: string | null; phone: string | null; whatsapp: string | null; address: string | null; hours: string | null };
  social_links: Partial<Record<"instagram" | "facebook" | "youtube" | "pinterest", string | null>>;
  default_product_sort: ProductSort;
  currency_code: string;
  guest_checkout_enabled: boolean;
  whatsapp_ordering_enabled: boolean;
  shipping?: { free_shipping_threshold?: string | null; shipping_message?: string; delivery_estimate?: string };
  order_policies?: {
    cancellation_enabled?: boolean;
    returns_enabled?: boolean;
    exchanges_enabled?: boolean;
    return_window_days?: number;
    reasons?: string[];
    policy_note?: string;
  };
  seo: { title_suffix?: string | null; default_description?: string | null };
  og_image: ProductImage | null;
  menus: Record<"header" | "footer" | "mobile", PublicLink[]>;
}

interface PublicCollection {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  image: ProductImage | null;
}

interface PublishedSection {
  id: string;
  type: string;
  title: string | null;
  subtitle: string | null;
  settings: Record<string, unknown>;
  desktop_image: ProductImage | null;
  mobile_image: ProductImage | null;
  products: ProductSummary[];
  categories: Category[];
  collections: PublicCollection[];
  collection: PublicCollection | null;
  view_all_href: string | null;
}

export interface PublishedHomepage {
  published: boolean;
  published_at: string | null;
  sections: PublishedSection[];
}

// --- helpers ----------------------------------------------------------------------------------

const THEMES: Theme[] = ["navy", "blush", "gold", "ivory"];
const ARTS = ["dress", "tee", "romper", "skirt"] as const;

/** A CMS image as the section's frame shows it: the admin crop when saved, else the original. */
function media(image: ProductImage | null | undefined, fallbackAlt: string, frame?: ImageFrame): MediaRef | null {
  if (!image) return null;
  const framed = frame ? framedImage(image, frame) : image;
  return { src: framed.url, alt: image.alt_text ?? fallbackAlt, width: framed.width, height: framed.height };
}

function str(value: unknown): string | undefined {
  return typeof value === "string" && value.trim() ? value : undefined;
}

function theme(value: unknown, fallback: Theme): Theme {
  return THEMES.includes(value as Theme) ? (value as Theme) : fallback;
}

function cta(value: unknown): LinkItem | undefined {
  if (!value || typeof value !== "object") return undefined;
  const { label, href } = value as { label?: unknown; href?: unknown };
  return str(label) && str(href) ? { label: label as string, href: href as string } : undefined;
}

function list<T>(value: unknown): T[] {
  return Array.isArray(value) ? (value as T[]) : [];
}

function links(items: PublicLink[]): LinkItem[] {
  return items
    .filter((item) => item.href)
    .map((item) => ({ label: item.label, href: item.href as string, openInNewTab: item.open_in_new_tab }));
}

// --- sections ---------------------------------------------------------------------------------

export function mapSections(homepage: PublishedHomepage): HomepageSection[] {
  const out: HomepageSection[] = [];
  for (const section of homepage.sections) {
    const s = section.settings;
    const title = section.title ?? "";
    switch (section.type) {
      case "hero_banner": {
        const headline = (s.headline ?? {}) as { lead?: string; highlight?: string; trail?: string };
        out.push({
          id: section.id,
          type: "hero",
          visible: true,
          eyebrow: str(s.eyebrow),
          headline: { lead: headline.lead ?? title, highlight: headline.highlight ?? "", trail: headline.trail },
          body: str(s.body) ?? section.subtitle ?? "",
          primaryCta: cta(s.primary_cta),
          secondaryCta: cta(s.secondary_cta),
          trust: list<{ icon: IconName; label: string }>(s.trust),
          image: media(section.desktop_image, title, "hero"),
          mobileImage: media(section.mobile_image, title, "hero"),
          theme: theme(s.theme, "blush"),
          layout: s.layout === "image-left" ? "image-left" : "image-right",
        });
        break;
      }
      case "category_grid":
        out.push({
          id: section.id,
          type: "category_showcase",
          visible: true,
          eyebrow: str(s.eyebrow),
          title: title || "Shop by category",
          limit: 12,
          categories: section.categories,
          showViewAll: s.show_view_all !== false,
        });
        break;
      case "product_carousel":
      case "product_grid":
        out.push({
          id: section.id,
          type: "product_rail",
          visible: true,
          eyebrow: str(s.eyebrow),
          title,
          subtitle: section.subtitle ?? undefined,
          products: section.products,
          cta: cta(s.cta) ?? (section.view_all_href ? { label: "View all", href: section.view_all_href } : undefined),
          layout: section.type === "product_carousel" ? "carousel" : "grid",
          theme: theme(s.theme, "ivory"),
        });
        break;
      case "editorial_banner":
      case "promo_banner":
        out.push({
          id: section.id,
          type: "promo_banner",
          visible: true,
          eyebrow: str(s.eyebrow),
          title,
          body: str(s.body) ?? section.subtitle ?? undefined,
          cta: cta(s.cta),
          image: media(section.desktop_image, title, "banner"),
          theme: theme(s.theme, "navy"),
          imagePosition: s.image_position === "left" ? "left" : "right",
        });
        break;
      case "collection_showcase":
        out.push({
          id: section.id,
          type: "featured_collections",
          visible: true,
          eyebrow: str(s.eyebrow),
          title: title || "Featured collections",
          items: section.collections.map((c, i) => ({
            title: c.name,
            caption: c.description ?? undefined,
            href: `/collections/${c.slug}`,
            image: media(c.image, c.name, "collection"),
            theme: THEMES[i % THEMES.length]!,
            art: ARTS[i % ARTS.length]!,
          })),
        });
        break;
      case "occasion_collection":
        if (!section.collection) break; // collection unpublished: nothing to spotlight
        out.push({
          id: section.id,
          type: "occasion",
          visible: true,
          eyebrow: str(s.eyebrow),
          title: title || section.collection.name,
          body: str(s.body) ?? section.collection.description ?? undefined,
          cta:
            cta(s.cta) ??
            (section.view_all_href ? { label: "Explore the collection", href: section.view_all_href } : undefined),
          image: media(section.desktop_image ?? section.collection.image, section.collection.name, "banner"),
          theme: theme(s.theme, "blush"),
          products: section.products,
        });
        break;
      case "trust_strip":
        out.push({
          id: section.id,
          type: "assurances",
          visible: true,
          title: section.title ?? undefined,
          items: list<{ icon: IconName; title: string; text?: string }>(s.items).map((i) => ({
            icon: i.icon,
            title: i.title,
            text: i.text ?? "",
          })),
        });
        break;
      case "testimonials":
        out.push({
          id: section.id,
          type: "testimonials",
          visible: true,
          title: title || "Words from Twinkle families",
          items: list<{ quote: string; author: string; context?: string }>(s.items),
        });
        break;
      case "faq":
        out.push({
          id: section.id,
          type: "faq",
          visible: true,
          title: title || "Frequently asked questions",
          items: list<{ question: string; answer: string }>(s.items),
        });
        break;
      case "announcement":
        if (!str(s.message)) break;
        out.push({
          id: section.id,
          type: "announcement_strip",
          visible: true,
          message: s.message as string,
          link: cta(s.link),
          theme: theme(s.theme, "navy"),
        });
        break;
      case "contact":
        out.push({
          id: section.id,
          type: "contact",
          visible: true,
          title: title || "Get in touch",
          body: str(s.body),
          showWhatsapp: s.show_whatsapp !== false,
          showPhone: s.show_phone !== false,
          showEmail: s.show_email !== false,
        });
        break;
      case "rich_text":
        if (!str(s.body)) break;
        out.push({
          id: section.id,
          type: "rich_text",
          visible: true,
          title: section.title ?? undefined,
          body: s.body as string,
          alignment: s.alignment === "left" ? "left" : "center",
        });
        break;
      default:
        break; // unknown types from a newer CMS are skipped safely
    }
  }
  return out;
}

// --- site -------------------------------------------------------------------------------------

export function mapSite(site: PublicSite, fallback: SiteContent, homepage: PublishedHomepage | null): SiteContent {
  const footerColumns = site.menus.footer
    .filter((item) => !item.href && item.children.length > 0)
    .map((item) => ({ title: item.label, links: links(item.children) }));
  const footerLinks = links(site.menus.footer.filter((item) => item.children.length === 0));
  const primary = links(site.menus.header);
  const mobile = links(site.menus.mobile);
  const announcement = site.announcement;
  const social = (Object.entries(site.social_links) as [SiteContent["footer"]["social"][number]["network"], string | null][])
    .filter(([, href]) => Boolean(href))
    .map(([network, href]) => ({ network, href: href as string }));

  return {
    ...fallback,
    source: "cms",
    brand: {
      name: site.store_name,
      tagline: site.tagline ?? "",
      description: site.seo.default_description || fallback.brand.description,
      logo: media(site.logo, site.store_name),
      faviconUrl: site.favicon?.url ?? null,
    },
    theme: site.theme,
    seo: {
      titleSuffix: site.seo.title_suffix || site.store_name,
      description: site.seo.default_description ?? "",
      ogImageUrl: site.og_image?.url ?? null,
    },
    defaultSort: site.default_product_sort,
    commerce: {
      // The public contact WhatsApp number is only exposed when ordering is enabled.
      whatsappOrdering: Boolean(site.whatsapp_ordering_enabled && site.contact.whatsapp),
      guestCheckout: site.guest_checkout_enabled,
      currency: site.currency_code || "INR",
      shipping: {
        freeThreshold: site.shipping?.free_shipping_threshold ?? null,
        message: site.shipping?.shipping_message ?? "",
        estimate: site.shipping?.delivery_estimate ?? "",
      },
      orderPolicies: {
        cancellation: Boolean(site.order_policies?.cancellation_enabled),
        returns: Boolean(site.order_policies?.returns_enabled),
        exchanges: Boolean(site.order_policies?.exchanges_enabled),
        returnWindowDays: site.order_policies?.return_window_days ?? 7,
        reasons: site.order_policies?.reasons ?? [],
        note: site.order_policies?.policy_note ?? "",
      },
    },
    announcement: {
      visible: Boolean(announcement.enabled && announcement.message),
      message: announcement.message ?? "",
      link:
        announcement.link_href && announcement.link_label
          ? { label: announcement.link_label, href: announcement.link_href }
          : undefined,
    },
    navigation: {
      primary: primary.length > 0 ? primary : fallback.navigation.primary,
      mobile: mobile.length > 0 ? mobile : primary.length > 0 ? primary : fallback.navigation.mobile,
    },
    homepage: homepage?.published ? { sections: mapSections(homepage) } : fallback.homepage,
    footer: {
      ...fallback.footer,
      columns: footerColumns.length > 0 ? footerColumns : fallback.footer.columns,
      policies: footerColumns.length > 0 ? footerLinks : fallback.footer.policies,
      social,
    },
    contact: site.contact,
  };
}
