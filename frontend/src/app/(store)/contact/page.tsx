import type { Metadata } from "next";
import { MessageCircle } from "lucide-react";
import { Suspense } from "react";

import { CmsPageArticle, ContactCard, hasContactDetails } from "@/components/content/CmsPage";
import { ButtonLink } from "@/components/ui/Button";
import { ContentSkeleton } from "@/components/ui/Feedback";
import { InfoPage } from "@/components/ui/InfoPage";
import { getSiteContent } from "@/lib/content";
import { findPublishedPage } from "@/lib/content/pages";

/** Contact Us: the CMS page "contact" (or "contact-us") plus contact details from store settings. */
const SLUGS = ["contact", "contact-us"];

export async function generateMetadata(): Promise<Metadata> {
  const [page, content] = await Promise.all([findPublishedPage(SLUGS), getSiteContent()]);
  return {
    title: page?.seo_title ?? page?.title ?? "Contact us",
    description: page?.seo_description ?? `How to reach ${content.brand.name}.`,
    alternates: { canonical: "/contact" },
  };
}

export default function ContactPage() {
  return (
    <Suspense fallback={<ContentSkeleton />}>
      <ContactBody />
    </Suspense>
  );
}

async function ContactBody() {
  const [page, content] = await Promise.all([findPublishedPage(SLUGS), getSiteContent()]);
  const crumbs = [{ label: "Home", href: "/" }, { label: "Contact us" }];
  const details = hasContactDetails(content.contact);

  if (!page && !details) {
    return (
      <InfoPage
        breadcrumbs={crumbs}
        icon={<MessageCircle aria-hidden="true" size={26} />}
        title="Contact us"
        description="Our contact details are being updated. Please check back soon."
        action={<ButtonLink href="/shop">Continue shopping</ButtonLink>}
      />
    );
  }
  return (
    <CmsPageArticle title={page?.title ?? "Contact us"} blocks={page?.content.blocks} breadcrumbs={crumbs}>
      {details && <ContactCard contact={content.contact} />}
    </CmsPageArticle>
  );
}
