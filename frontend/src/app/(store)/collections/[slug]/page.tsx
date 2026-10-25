import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { ListingSkeleton, ListingView } from "@/components/catalog/ListingView";
import { getCollection, getFacets, listProducts } from "@/lib/catalog/api";
import { buildFilterOptions } from "@/lib/catalog/filters";
import { parseListingQuery } from "@/lib/catalog/query";
import { getSiteContent } from "@/lib/content";

/** Published collection (GET /collections/{slug}) + its products in the collection's own order. */
export async function generateMetadata({ params }: PageProps<"/collections/[slug]">): Promise<Metadata> {
  const { slug } = await params;
  const result = await getCollection(slug);
  if (!result.ok) return { title: "Collection" };
  const collection = result.data;
  const description = collection.seo_description ?? collection.description ?? undefined;
  return {
    title: collection.seo_title ?? collection.name,
    description,
    alternates: { canonical: `/collections/${collection.slug}` },
    openGraph: {
      title: collection.seo_title ?? collection.name,
      description,
      url: `/collections/${collection.slug}`,
      images: collection.image
        ? [{ url: collection.image.url, width: collection.image.width, height: collection.image.height }]
        : undefined,
    },
  };
}

export default function CollectionPage({ params, searchParams }: PageProps<"/collections/[slug]">) {
  return (
    <Suspense fallback={<ListingSkeleton />}>
      <CollectionListing params={params} searchParams={searchParams} />
    </Suspense>
  );
}

async function CollectionListing({ params, searchParams }: PageProps<"/collections/[slug]">) {
  const [{ slug }, search, content] = await Promise.all([params, searchParams, getSiteContent()]);
  const query = parseListingQuery(search, content.defaultSort);
  const [collection, result, facets] = await Promise.all([
    getCollection(slug),
    listProducts(query, { collection: slug }),
    getFacets({ collection: slug, q: query.q }),
  ]);
  if (!collection.ok && collection.status === 404) notFound(); // unpublished or unknown

  const title = collection.ok ? collection.data.name : "Collection";
  return (
    <ListingView
      title={title}
      eyebrow="Collection"
      description={collection.ok ? collection.data.description : null}
      breadcrumbs={[{ label: "Home", href: "/" }, { label: "Shop", href: "/shop" }, { label: title }]}
      basePath={`/collections/${slug}`}
      query={query}
      result={result}
      options={buildFilterOptions(facets)}
      emptyMessage={{
        title: "New styles are on their way",
        description: "This collection is being curated — check back soon.",
      }}
    />
  );
}
