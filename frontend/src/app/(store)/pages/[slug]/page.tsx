import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { FileText } from "lucide-react";
import { Suspense } from "react";

import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { ButtonLink } from "@/components/ui/Button";
import { Accordion } from "@/components/ui/Form";
import { InfoPage } from "@/components/ui/InfoPage";
import { getSiteContent } from "@/lib/content";
import { type PageBlock, getPublishedPage } from "@/lib/content/pages";
import styles from "./page.module.css";

/**
 * Website pages from the CMS `website_pages` table (published only). Content is structured
 * blocks rendered as plain text — never raw HTML.
 */
export async function generateMetadata({ params }: PageProps<"/pages/[slug]">): Promise<Metadata> {
  const { slug } = await params;
  const page = await getPublishedPage(slug);
  if (page && page !== "unavailable") {
    return { title: page.seo_title ?? page.title, description: page.seo_description ?? undefined };
  }
  return { title: "Page" };
}

export default function WebsitePage({ params }: PageProps<"/pages/[slug]">) {
  return (
    <Suspense fallback={null}>
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
    <article className={`container-narrow ${styles.page}`}>
      <Breadcrumbs items={[{ label: "Home", href: "/" }, { label: page.title }]} />
      <h1 className={styles.title}>{page.title}</h1>
      <div className={styles.body}>
        {(page.content.blocks ?? []).map((block, index) => (
          <Block key={index} block={block} />
        ))}
      </div>
    </article>
  );
}

function Block({ block }: { block: PageBlock }) {
  switch (block.type) {
    case "heading":
      return block.level === 3 ? <h3 className={styles.h3}>{block.text}</h3> : <h2 className={styles.h2}>{block.text}</h2>;
    case "paragraph":
      return <p>{block.text}</p>;
    case "list":
      return block.ordered ? (
        <ol className={styles.list}>
          {block.items.map((item, i) => (
            <li key={i}>{item}</li>
          ))}
        </ol>
      ) : (
        <ul className={styles.list}>
          {block.items.map((item, i) => (
            <li key={i}>{item}</li>
          ))}
        </ul>
      );
    case "faq":
      return (
        <div className={styles.faq}>
          {block.items.map((item, i) => (
            <Accordion key={i} title={item.question}>
              <p>{item.answer}</p>
            </Accordion>
          ))}
        </div>
      );
    case "callout":
      return <p className={styles.callout}>{block.text}</p>;
    default:
      return null;
  }
}
