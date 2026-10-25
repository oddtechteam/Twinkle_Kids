import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { RotateCcw, Star } from "lucide-react";
import { type ReactNode, Suspense } from "react";

import { ProductExperience } from "@/components/product/ProductExperience";
import { ProductGrid, ProductGridSkeleton } from "@/components/product/ProductGrid";
import { ProductSkeleton } from "@/components/product/ProductSkeleton";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { ButtonLink } from "@/components/ui/Button";
import { EmptyState, Skeleton } from "@/components/ui/Feedback";
import { Accordion } from "@/components/ui/Form";
import { Motif } from "@/components/ui/Motif";
import { SectionHeading } from "@/components/ui/SectionHeading";
import type { CategoryRef, ProductDetail, ReviewSummary } from "@/lib/api/types";
import { cardFromSummary } from "@/lib/catalog/adapters";
import { getProduct, getReviews, getShippingRules, getSitemap, selectProducts } from "@/lib/catalog/api";
import { getSiteContent } from "@/lib/content";
import { formatMoney } from "@/lib/format";
import { siteUrl } from "@/lib/site";
import styles from "./page.module.css";

export async function generateMetadata({ params }: PageProps<"/products/[slug]">): Promise<Metadata> {
  const { slug } = await params;
  const result = await getProduct(slug);
  if (!result.ok) return { title: "Product", robots: { index: false } };
  const product = result.data;
  const title = product.seo_title ?? product.name;
  const description = product.seo_description ?? product.short_description ?? undefined;
  return {
    title,
    description,
    alternates: { canonical: `/products/${product.slug}` },
    openGraph: {
      type: "website",
      title,
      description,
      url: `/products/${product.slug}`,
      images: product.images.slice(0, 4).map((image) => ({
        url: image.url,
        width: image.width,
        height: image.height,
        alt: image.alt_text ?? product.name,
      })),
    },
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
  const [result, reviews] = await Promise.all([getProduct(slug), getReviews(slug)]);

  if (!result.ok) {
    if (result.status === 404) notFound(); // unknown, draft or archived product
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
  const collection = product.collections?.[0];
  const reviewSummary = reviews.ok && reviews.data.count > 0 ? reviews.data : null;

  return (
    <div className={styles.page}>
      <ProductJsonLd product={product} reviews={reviewSummary} brand={content.brand.name} />
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
            whatsappEnabled={content.commerce.whatsappOrdering}
            eyebrow={
              primary ? (
                <Link href={`/category/${primary.slug}`} className={styles.eyebrow}>
                  <Motif size={12} /> {primary.name}
                </Link>
              ) : undefined
            }
            details={
              <ProductDetails
                product={product}
                shipping={
                  <Suspense fallback={<Skeleton height="3rem" radius="var(--radius-md)" />}>
                    <DeliveryAndReturns />
                  </Suspense>
                }
              />
            }
          />
        </div>
      </div>

      {reviewSummary && <Reviews summary={reviewSummary} />}

      {collection && (
        <Suspense fallback={<RelatedSkeleton />}>
          <MoreProducts
            title={`More from ${collection.name}`}
            eyebrow="From the same collection"
            scope={{ collection: collection.slug }}
            link={`/collections/${collection.slug}`}
            excludeSlug={product.slug}
          />
        </Suspense>
      )}
      {primary && (
        <Suspense fallback={<RelatedSkeleton />}>
          <MoreProducts
            title="You may also like"
            eyebrow="Complete the look"
            scope={{ category: primary.slug }}
            link={`/category/${primary.slug}`}
            excludeSlug={product.slug}
          />
        </Suspense>
      )}
    </div>
  );
}

/** Product-specific fabric & care, if the catalogue provides it (rich_content.fabric / .care). */
function careDetails(product: ProductDetail): { fabric: string[]; care: string[] } {
  const read = (value: unknown): string[] =>
    typeof value === "string"
      ? value.split(/\n+/).map((line) => line.trim()).filter(Boolean)
      : Array.isArray(value)
        ? value.filter((item): item is string => typeof item === "string" && item.trim() !== "")
        : [];
  const rich = product.rich_content ?? {};
  return { fabric: read(rich.fabric ?? rich.material), care: read(rich.care ?? rich.care_instructions) };
}

function ProductDetails({ product, shipping }: { product: ProductDetail; shipping: ReactNode }) {
  const paragraphs = (product.description ?? "").split(/\n{2,}/).map((p) => p.trim()).filter(Boolean);
  const { fabric, care } = careDetails(product);
  const collections = product.collections ?? [];
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
      {(fabric.length > 0 || care.length > 0) && (
        <Accordion title="Fabric & care">
          <div className={styles.prose}>
            {fabric.length > 0 && (
              <div>
                <p className={styles.subhead}>Fabric</p>
                <ul className={styles.list}>
                  {fabric.map((line) => (
                    <li key={line}>{line}</li>
                  ))}
                </ul>
              </div>
            )}
            {care.length > 0 && (
              <div>
                <p className={styles.subhead}>Care</p>
                <ul className={styles.list}>
                  {care.map((line) => (
                    <li key={line}>{line}</li>
                  ))}
                </ul>
              </div>
            )}
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
              <dd>
                <RefLinks items={product.categories} base="/category" />
              </dd>
            </>
          )}
          {collections.length > 0 && (
            <>
              <dt>Collection</dt>
              <dd>
                <RefLinks items={collections} base="/collections" />
              </dd>
            </>
          )}
        </dl>
      </Accordion>
      <Accordion title="Delivery & returns">{shipping}</Accordion>
    </>
  );
}

function RefLinks({ items, base }: { items: CategoryRef[]; base: string }) {
  return (
    <>
      {items.map((item, index) => (
        <span key={item.id}>
          {index > 0 && ", "}
          <Link href={`${base}/${item.slug}`} className={styles.inlineLink}>
            {item.name}
          </Link>
        </span>
      ))}
    </>
  );
}

/** Delivery fees from the store's shipping rules, plus links to published policy pages. */
async function DeliveryAndReturns() {
  const [rules, sitemap] = await Promise.all([getShippingRules(), getSitemap()]);
  const pages = sitemap.ok ? sitemap.data.pages.map((p) => p.slug) : [];
  const shippingPage = pages.find((slug) => /shipping|delivery/.test(slug));
  const returnsPage = pages.find((slug) => /return|exchange|refund/.test(slug));
  const bands = rules.ok ? rules.data : [];

  if (bands.length === 0 && !shippingPage && !returnsPage) {
    return <p>Delivery charges and timelines are confirmed with your order.</p>;
  }
  return (
    <div className={styles.prose}>
      {bands.length > 0 && (
        <ul className={styles.list}>
          {bands.map((band) => (
            <li key={band.name}>
              {Number(band.fee) === 0 ? "Free delivery" : `Delivery ${formatMoney(band.fee)}`}
              {Number(band.min_order_amount) > 0 && band.max_order_amount
                ? ` on orders ${formatMoney(band.min_order_amount)} – ${formatMoney(band.max_order_amount)}`
                : Number(band.min_order_amount) > 0
                  ? ` on orders of ${formatMoney(band.min_order_amount)} or more`
                  : band.max_order_amount
                    ? ` on orders up to ${formatMoney(band.max_order_amount)}`
                    : ""}
            </li>
          ))}
        </ul>
      )}
      {(shippingPage || returnsPage) && (
        <p>
          {shippingPage && (
            <Link href={`/pages/${shippingPage}`} className={styles.inlineLink}>
              Shipping information
            </Link>
          )}
          {shippingPage && returnsPage && " · "}
          {returnsPage && (
            <Link href={`/pages/${returnsPage}`} className={styles.inlineLink}>
              Returns & exchanges
            </Link>
          )}
        </p>
      )}
    </div>
  );
}

function Stars({ rating, label }: { rating: number; label: string }) {
  return (
    <span className={styles.stars} role="img" aria-label={label}>
      {[1, 2, 3, 4, 5].map((n) => (
        <Star key={n} aria-hidden="true" size={16} className={n <= Math.round(rating) ? styles.starOn : styles.starOff} />
      ))}
    </span>
  );
}

function Reviews({ summary }: { summary: ReviewSummary }) {
  const average = Number(summary.average ?? 0);
  return (
    <section className={`section ${styles.reviews}`} aria-labelledby="reviews-title">
      <div className="container-narrow">
        <SectionHeading id="reviews-title" eyebrow="Loved by families" title="Customer reviews" />
        <p className={styles.reviewSummary}>
          <Stars rating={average} label={`Rated ${average.toFixed(1)} out of 5`} />
          <span>
            {average.toFixed(1)} · {summary.count} {summary.count === 1 ? "review" : "reviews"}
          </span>
        </p>
        <ul className={styles.reviewList}>
          {summary.items.map((review, index) => (
            <li key={`${review.created_at}-${index}`} className={styles.review}>
              <Stars rating={review.rating} label={`${review.rating} out of 5`} />
              {review.title && <p className={styles.reviewTitle}>{review.title}</p>}
              {review.body && <p>{review.body}</p>}
              <p className={styles.reviewMeta}>
                {review.author ?? "Verified customer"} ·{" "}
                {new Intl.DateTimeFormat("en-IN", { dateStyle: "medium" }).format(new Date(review.created_at))}
              </p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

/** schema.org Product data built only from live catalogue values. */
function ProductJsonLd({ product, reviews, brand }: { product: ProductDetail; reviews: ReviewSummary | null; brand: string }) {
  const url = `${siteUrl()}/products/${product.slug}`;
  const prices = product.variants.filter((v) => v.is_active).map((v) => Number(v.price.selling_price));
  const low = prices.length ? Math.min(...prices) : Number(product.price.selling_price);
  const high = prices.length ? Math.max(...prices) : low;
  const availability = product.in_stock ? "https://schema.org/InStock" : "https://schema.org/OutOfStock";
  const data = {
    "@context": "https://schema.org",
    "@type": "Product",
    name: product.name,
    sku: product.sku,
    description: product.short_description ?? product.description ?? undefined,
    image: product.images.map((image) => image.url),
    brand: { "@type": "Brand", name: brand },
    category: product.categories[0]?.name,
    offers:
      low === high
        ? { "@type": "Offer", url, priceCurrency: product.price.currency, price: low.toFixed(2), availability }
        : {
            "@type": "AggregateOffer",
            url,
            priceCurrency: product.price.currency,
            lowPrice: low.toFixed(2),
            highPrice: high.toFixed(2),
            offerCount: prices.length,
            availability,
          },
    aggregateRating: reviews?.average
      ? { "@type": "AggregateRating", ratingValue: reviews.average, reviewCount: reviews.count }
      : undefined,
  };
  return (
    <script
      type="application/ld+json"
      // JSON.stringify output with "<" escaped cannot break out of the script element.
      dangerouslySetInnerHTML={{ __html: JSON.stringify(data).replace(/</g, "\\u003c") }}
    />
  );
}

async function MoreProducts({
  title,
  eyebrow,
  scope,
  link,
  excludeSlug,
}: {
  title: string;
  eyebrow: string;
  scope: { category?: string; collection?: string };
  link: string;
  excludeSlug: string;
}) {
  const result = await selectProducts({ ...scope, limit: 5 });
  if (!result.ok) return null;
  const products = result.data.items.filter((p) => p.slug !== excludeSlug).slice(0, 4);
  if (products.length === 0) return null;
  const id = `more-${scope.collection ?? scope.category}`;
  return (
    <section className={`section ${styles.related}`} aria-labelledby={id}>
      <div className="container">
        <SectionHeading id={id} eyebrow={eyebrow} title={title} link={{ label: "View more", href: link }} />
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

