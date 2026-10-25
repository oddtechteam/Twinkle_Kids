import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { FileText } from "lucide-react";
import { Suspense } from "react";

import { CmsPageArticle } from "@/components/content/CmsPage";
import { ButtonLink } from "@/components/ui/Button";
import { ContentSkeleton } from "@/components/ui/Feedback";
import { InfoPage } from "@/components/ui/InfoPage";
import { getSiteContent } from "@/lib/content";
import { getPublishedPage } from "@/lib/content/pages";

/**
 * Website pages from the CMS `website_pages` table (published only). Content is structured
 * blocks rendered as plain text — never raw HTML.
 */
export async function generateMetadata({ params }: PageProps<"/pages/[slug]">): Promise<Metadata> {
  const { slug } = await params;
  const page = await getPublishedPage(slug);
  if (page && page !== "unavailable") {
    return {
      title: page.seo_title ?? page.title,
      description: page.seo_description ?? undefined,
      alternates: { canonical: `/pages/${page.slug}` },
    };
  }
  return { title: "Page", robots: { index: false } };
}

export default function WebsitePage({ params }: PageProps<"/pages/[slug]">) {
  return (
    <Suspense fallback={<ContentSkeleton />}>
      <WebsitePageBody params={params} />
    </Suspense>
  );
}

async function WebsitePageBody({ params }: Pick<PageProps<"/pages/[slug]">, "params">) {
  const [{ slug }, content] = await Promise.all([params, getSiteContent()]);
  const page = await getPublishedPage(slug);

  if (page === null || page === "unavailable") {
    // Not published yet: say so for pages linked from the site, otherwise 404.
    const placeholder = content.pages[slug];
    if (!placeholder) notFound();
    return (
      <InfoPage
        breadcrumbs={[{ label: "Home", href: "/" }, { label: placeholder.title }]}
        icon={<FileText aria-hidden="true" size={26} />}
        title={placeholder.title}
        description={`${placeholder.summary} This page is being prepared and will be published soon.`}
        action={<ButtonLink href="/shop">Continue shopping</ButtonLink>}
      />
    );
  }

  return (
    <CmsPageArticle
      title={page.title}
      blocks={page.content.blocks}
      breadcrumbs={[{ label: "Home", href: "/" }, { label: page.title }]}
    />
  );
}
