import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { RotateCcw } from "lucide-react";
import { Suspense } from "react";

import { ProductExperience } from "@/components/product/ProductExperience";
import { ProductGrid, ProductGridSkeleton } from "@/components/product/ProductGrid";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { ButtonLink } from "@/components/ui/Button";
import { EmptyState, Skeleton } from "@/components/ui/Feedback";
import { Accordion } from "@/components/ui/Form";
import { Motif } from "@/components/ui/Motif";
import { SectionHeading } from "@/components/ui/SectionHeading";
import type { ProductDetail } from "@/lib/api/types";
import { cardFromSummary } from "@/lib/catalog/adapters";
import { getProduct, selectProducts } from "@/lib/catalog/api";
import { getSiteContent } from "@/lib/content";
import styles from "./page.module.css";

export async function generateMetadata({ params }: PageProps<"/products/[slug]">): Promise<Metadata> {
  const { slug } = await params;
  const result = await getProduct(slug);
  if (!result.ok) return { title: "Product" };
  const product = result.data;
  const image = product.images[0];
  return {
    title: product.seo_title ?? product.name,
    description: product.seo_description ?? product.short_description ?? undefined,
    openGraph: image ? { images: [{ url: image.url, width: image.width, height: image.height }] } : undefined,
  };
}

export default function ProductPage({ params }: PageProps<"/products/[slug]">) {
  return (
    <Suspense fallback={<ProductSkeleton />}>
      <ProductView params={params} />
    </Suspense>
  );
}

async function ProductView({ params }: Pick<PageProps<"/products/[slug]">, "params">) {
  const [{ slug }, content] = await Promise.all([params, getSiteContent()]);
  const result = await getProduct(slug);

  if (!result.ok) {
    if (result.status === 404) notFound();
    return (
      <div className={`container ${styles.page}`}>
        <EmptyState
          tone="error"
          title="We couldn't load this style"
          description="Please try again in a moment."
          action={
            <ButtonLink href={`/products/${slug}`} iconStart={<RotateCcw aria-hidden="true" />}>
              Try again
            </ButtonLink>
          }
        />
      </div>
    );
  }

  const product = result.data;
  const primary = product.categories[0];

  return (
    <div className={styles.page}>
      <div className="container">
        <Breadcrumbs
          items={[
            { label: "Home", href: "/" },
            primary ? { label: primary.name, href: `/category/${primary.slug}` } : { label: "Shop", href: "/shop" },
            { label: product.name },
          ]}
        />
        <div className={styles.main}>
          <ProductExperience
            product={product}
            notes={content.catalog.purchaseNotes}
            eyebrow={
              primary ? (
                <Link href={`/category/${primary.slug}`} className={styles.eyebrow}>
                  <Motif size={12} /> {primary.name}
                </Link>
              ) : undefined
            }
            details={<ProductDetails product={product} />}
          />
        </div>
      </div>

      {primary && (
        <Suspense fallback={<RelatedSkeleton />}>
          <RelatedProducts categorySlug={primary.slug} excludeSlug={product.slug} />
        </Suspense>
      )}
    </div>
  );
}

function ProductDetails({ product }: { product: ProductDetail }) {
  const paragraphs = (product.description ?? "").split(/\n{2,}/).map((p) => p.trim()).filter(Boolean);
  return (
    <>
      {paragraphs.length > 0 && (
        <Accordion title="Description" defaultOpen>
          <div className={styles.prose}>
            {paragraphs.map((paragraph, index) => (
              <p key={index}>{paragraph}</p>
            ))}
          </div>
        </Accordion>
      )}
      {product.sizes.length > 0 && (
        <Accordion title="Size & fit">
          <p>Available in {product.sizes.join(", ")}.</p>
          {product.size_chart && <p>Open the size guide above for measurements.</p>}
        </Accordion>
      )}
      <Accordion title="Product details">
        <dl className={styles.facts}>
          <dt>Product code</dt>
          <dd>{product.sku}</dd>
          {product.colours.length > 0 && (
            <>
              <dt>Colours</dt>
              <dd>{product.colours.join(", ")}</dd>
            </>
          )}
          {product.categories.length > 0 && (
            <>
              <dt>Category</dt>
              <dd>{product.categories.map((c) => c.name).join(", ")}</dd>
            </>
          )}
        </dl>
      </Accordion>
    </>
  );
}

async function RelatedProducts({ categorySlug, excludeSlug }: { categorySlug: string; excludeSlug: string }) {
  const result = await selectProducts({ category: categorySlug, limit: 5 });
  if (!result.ok) return null;
  const products = result.data.items.filter((p) => p.slug !== excludeSlug).slice(0, 4);
  if (products.length === 0) return null;
  return (
    <section className={`section ${styles.related}`} aria-labelledby="related-title">
      <div className="container">
        <SectionHeading
          id="related-title"
          eyebrow="Complete the look"
          title="You may also like"
          link={{ label: "View more", href: `/category/${categorySlug}` }}
        />
        <ProductGrid products={products.map(cardFromSummary)} />
      </div>
    </section>
  );
}

function RelatedSkeleton() {
  return (
    <div className="section container" aria-hidden="true">
      <ProductGridSkeleton count={4} />
    </div>
  );
}

function ProductSkeleton() {
  return (
    <div className={`container ${styles.page}`} aria-busy="true" aria-label="Loading product">
      <Skeleton width="14rem" height="0.9rem" />
      <div className={styles.skeleton}>
        <Skeleton height="auto" radius="var(--radius-xl)" className={styles.skeletonImage} />
        <div className={styles.skeletonInfo}>
          <Skeleton width="70%" height="2.5rem" radius="var(--radius-pill)" />
          <Skeleton width="35%" height="1.75rem" radius="var(--radius-pill)" />
          <Skeleton height="6rem" radius="var(--radius-lg)" />
          <Skeleton height="3.25rem" radius="var(--radius-pill)" />
        </div>
      </div>
    </div>
  );
}
