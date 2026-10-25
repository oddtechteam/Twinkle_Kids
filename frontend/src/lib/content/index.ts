/**
 * Site content access for the storefront.
 *
 * Reads the *published* CMS (site settings + latest homepage publication) and caches it under
 * the `site-content` tag. Publishing in the admin triggers /api/revalidate, which expires the
 * tag so the next request renders the new content. When the CMS cannot be reached (or nothing
 * has been published yet) the clearly labelled development fixture is used instead.
 */

import { cacheLife, cacheTag } from "next/cache";

import { apiFetch } from "@/lib/api/client";
import { type PublicSite, type PublishedHomepage, mapSite } from "./cms";
import { developmentContent } from "./fixtures/development-content";
import type { HomepageSection, SiteContent } from "./types";

/**
 * Outside development the fixture only supplies the store shell (name, safe links). Its
 * homepage is never shown in production: an unreachable or unpublished CMS renders an honest
 * empty state instead of editorial copy nobody approved.
 */
const isDevelopment = process.env.NODE_ENV !== "production";

function shellOnly(content: SiteContent): SiteContent {
  return {
    ...content,
    announcement: { ...content.announcement, visible: false },
    homepage: { sections: [] },
  };
}

export const SITE_CONTENT_TAG = "site-content";

export async function getSiteContent(): Promise<SiteContent> {
  "use cache";
  cacheTag(SITE_CONTENT_TAG);
  cacheLife("minutes");

  try {
    const [site, homepage] = await Promise.all([
      apiFetch<PublicSite>("/content/site"),
      apiFetch<PublishedHomepage>("/content/homepage").catch(() => null),
    ]);
    const fallback = isDevelopment ? developmentContent : shellOnly(developmentContent);
    return mapSite(site, fallback, homepage);
  } catch {
    return isDevelopment ? developmentContent : shellOnly(developmentContent);
  }
}

/** Sections the storefront should render, in CMS-defined order. */
export function visibleSections(content: SiteContent): HomepageSection[] {
  return content.homepage.sections.filter((section) => {
    if (!section.visible) return false;
    switch (section.type) {
      case "testimonials":
      case "faq":
      case "featured_collections":
        return section.items.length > 0;
      case "assurances":
        return section.items.length > 0;
      case "occasion":
        return section.products.length > 0 || section.image !== null;
      case "contact": {
        const c = content.contact;
        return Boolean(
          (section.showWhatsapp !== false && c.whatsapp) ||
            (section.showPhone !== false && c.phone) ||
            (section.showEmail !== false && c.email),
        );
      }
      default:
        return true;
    }
  });
}

export type { SiteContent } from "./types";
