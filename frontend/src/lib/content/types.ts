/**
 * Storefront content model. Filled from the published CMS (`/content/site`,
 * `/content/homepage`) by ./cms.ts, or from the development fixture when the CMS is
 * unreachable or nothing has been published yet.
 */

import type { Category, ProductSort, ProductSummary } from "@/lib/api/types";
import type { ThemeColours } from "./theme";

export interface LinkItem {
  label: string;
  href: string;
  openInNewTab?: boolean;
}

export interface MediaRef {
  /** Absolute image URL (e.g. Neon Object Storage `media` bucket). */
  src: string;
  alt: string;
  width: number;
  height: number;
  /** CSS object-position, e.g. "50% 30%", for art-directed cropping. */
  focal?: string;
}

export type Theme = "ivory" | "blush" | "navy" | "gold";
export type IconName =
  | "sparkles"
  | "ruler"
  | "message-circle"
  | "gift"
  | "heart"
  | "shield-check"
  | "shirt"
  | "star";

export interface Announcement {
  visible: boolean;
  message: string;
  link?: LinkItem;
}

export interface HeroMessage {
  icon: IconName;
  text: string;
}

export interface HeroSection {
  id: string;
  type: "hero";
  visible: boolean;
  eyebrow?: string;
  headline: { lead: string; highlight: string; trail?: string };
  body: string;
  primaryCta?: LinkItem;
  secondaryCta?: LinkItem;
  trust: { icon: IconName; label: string }[];
  /** Short floating messages around the interactive stage (shown when no photo is set). */
  messages?: HeroMessage[];
  image: MediaRef | null; // desktop
  mobileImage?: MediaRef | null;
  theme: Theme;
  layout: "image-right" | "image-left";
}

export interface CategoryShowcaseSection {
  id: string;
  type: "category_showcase";
  visible: boolean;
  eyebrow?: string;
  title: string;
  limit: number;
  /** Resolved by the CMS (ordered); when absent the storefront loads top-level categories. */
  categories?: Category[];
  showViewAll?: boolean;
}

export interface ProductRailSection {
  id: string;
  type: "product_rail";
  visible: boolean;
  eyebrow?: string;
  title: string;
  subtitle?: string;
  /** Fixture sections select products by rule; CMS sections arrive with products resolved. */
  selection?: { sort: ProductSort; category?: string; collection?: string; limit: number };
  products?: ProductSummary[];
  cta?: LinkItem;
  layout: "carousel" | "grid";
  theme: Theme;
}

export interface CollectionTile {
  title: string;
  caption?: string;
  href: string;
  image: MediaRef | null;
  theme: Theme;
  art: "dress" | "tee" | "romper" | "skirt";
}

export interface FeaturedCollectionsSection {
  id: string;
  type: "featured_collections";
  visible: boolean;
  eyebrow?: string;
  title: string;
  items: CollectionTile[];
}

export interface PromoBannerSection {
  id: string;
  type: "promo_banner";
  visible: boolean;
  eyebrow?: string;
  title: string;
  body?: string;
  cta?: LinkItem;
  image: MediaRef | null;
  theme: Theme;
  imagePosition?: "left" | "right";
}

export interface OccasionSection {
  id: string;
  type: "occasion";
  visible: boolean;
  eyebrow?: string;
  title: string;
  body?: string;
  cta?: LinkItem;
  image: MediaRef | null;
  theme: Theme;
  products: ProductSummary[];
}

export interface AssurancesSection {
  id: string;
  type: "assurances";
  visible: boolean;
  title?: string;
  items: { icon: IconName; title: string; text: string }[];
}

export interface TestimonialsSection {
  id: string;
  type: "testimonials";
  visible: boolean;
  title: string;
  /** Only real, approved customer reviews. The section is hidden while this is empty. */
  items: { quote: string; author: string; context?: string }[];
}

export interface FaqSection {
  id: string;
  type: "faq";
  visible: boolean;
  title: string;
  items: { question: string; answer: string }[];
}

export interface AnnouncementStripSection {
  id: string;
  type: "announcement_strip";
  visible: boolean;
  message: string;
  link?: LinkItem;
  theme: Theme;
}

export interface RichTextSection {
  id: string;
  type: "rich_text";
  visible: boolean;
  title?: string;
  body: string;
  alignment: "left" | "center";
}

export interface ContactSection {
  id: string;
  type: "contact";
  visible: boolean;
  title: string;
  body?: string;
  showWhatsapp?: boolean;
  showPhone?: boolean;
  showEmail?: boolean;
}

export type HomepageSection =
  | HeroSection
  | CategoryShowcaseSection
  | ProductRailSection
  | FeaturedCollectionsSection
  | PromoBannerSection
  | OccasionSection
  | AssurancesSection
  | TestimonialsSection
  | FaqSection
  | AnnouncementStripSection
  | RichTextSection
  | ContactSection;

export interface ContactDetails {
  email: string | null;
  phone: string | null;
  whatsapp: string | null;
  address: string | null;
  hours: string | null;
}

export interface SiteContent {
  /** Where this content came from — "development-fixture" until the CMS is published. */
  source: "cms" | "development-fixture";
  brand: {
    name: string;
    tagline: string;
    description: string;
    logo?: MediaRef | null;
    faviconUrl?: string | null;
  };
  theme: ThemeColours;
  seo: { titleSuffix: string; description: string; ogImageUrl: string | null };
  defaultSort: ProductSort;
  announcement: Announcement;
  navigation: { primary: LinkItem[]; mobile: LinkItem[] };
  homepage: { sections: HomepageSection[] };
  catalog: {
    filterSizes: string[];
    filterColours: { name: string; hex: string }[];
    priceBands: { label: string; min: string | null; max: string | null }[];
    purchaseNotes: { icon: IconName; text: string }[];
  };
  footer: {
    blurb: string;
    columns: { title: string; links: LinkItem[] }[];
    policies: LinkItem[];
    social: { network: "instagram" | "facebook" | "youtube" | "pinterest"; href: string }[];
  };
  contact: ContactDetails;
  pages: Record<string, { title: string; summary: string }>;
}
