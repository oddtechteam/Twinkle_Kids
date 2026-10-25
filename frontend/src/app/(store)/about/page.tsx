import type { Metadata } from "next";
import { Heart } from "lucide-react";
import { Suspense } from "react";

import { CmsPageArticle } from "@/components/content/CmsPage";
import { ButtonLink } from "@/components/ui/Button";
import { ContentSkeleton } from "@/components/ui/Feedback";
import { InfoPage } from "@/components/ui/InfoPage";
import { getSiteContent } from "@/lib/content";
import { findPublishedPage } from "@/lib/content/pages";

/** About Us: the CMS page published as "about" (or "about-us"). */
const SLUGS = ["about", "about-us"];

export async function generateMetadata(): Promise<Metadata> {
  const [page, content] = await Promise.all([findPublishedPage(SLUGS), getSiteContent()]);
  return {
    title: page?.seo_title ?? page?.title ?? `About ${content.brand.name}`,
    description: page?.seo_description ?? content.brand.description,
    alternates: { canonical: "/about" },
  };
}

export default function AboutPage() {
  return (
    <Suspense fallback={<ContentSkeleton />}>
      <AboutBody />
    </Suspense>
  );
}

async function AboutBody() {
  const [page, content] = await Promise.all([findPublishedPage(SLUGS), getSiteContent()]);
  const crumbs = [{ label: "Home", href: "/" }, { label: "About us" }];

  if (!page) {
    return (
      <InfoPage
        breadcrumbs={crumbs}
        icon={<Heart aria-hidden="true" size={26} />}
        title={`About ${content.brand.name}`}
        description={content.brand.description}
        action={<ButtonLink href="/shop">Explore the collection</ButtonLink>}
      />
    );
  }
  return <CmsPageArticle title={page.title} blocks={page.content.blocks} breadcrumbs={crumbs} />;
}
