/** Published website pages (policies, size guide, FAQs) from the CMS. */

import { cacheLife, cacheTag } from "next/cache";

import { ApiError, apiFetch } from "@/lib/api/client";

export type PageBlock =
  | { type: "heading"; text: string; level: 2 | 3 }
  | { type: "paragraph"; text: string }
  | { type: "list"; ordered: boolean; items: string[] }
  | { type: "faq"; items: { question: string; answer: string }[] }
  | { type: "callout"; text: string };

export interface PublishedPage {
  slug: string;
  title: string;
  content: { blocks?: PageBlock[] };
  seo_title: string | null;
  seo_description: string | null;
  published_at: string | null;
}

/** Returns null when the page does not exist or is not published. */
export async function getPublishedPage(slug: string): Promise<PublishedPage | null | "unavailable"> {
  "use cache";
  cacheTag("site-content");
  cacheLife("minutes");
  try {
    return await apiFetch<PublishedPage>(`/content/pages/${encodeURIComponent(slug)}`);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    return "unavailable";
  }
}

/** The first published page among candidate slugs (e.g. "about" or "about-us"), else null. */
export async function findPublishedPage(slugs: string[]): Promise<PublishedPage | null> {
  for (const slug of slugs) {
    const page = await getPublishedPage(slug);
    if (page && page !== "unavailable") return page;
  }
  return null;
}
