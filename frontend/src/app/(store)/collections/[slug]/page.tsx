import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { ListingSkeleton, ListingView } from "@/components/catalog/ListingView";
import { getCollection, listProducts } from "@/lib/catalog/api";
import { parseListingQuery } from "@/lib/catalog/query";
import { getSiteContent } from "@/lib/content";

/** Published collection (GET /collections/{slug}) + its products in the collection's own order. */
export async function generateMetadata({ params }: PageProps<"/collections/[slug]">): Promise<Metadata> {
  const { slug } = await params;
  const result = await getCollection(slug);
  if (!result.ok) return { title: "Collection" };
  return {
    title: result.data.seo_title ?? result.data.name,
    description: result.data.seo_description ?? result.data.description ?? undefined,
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
  const [collection, result] = await Promise.all([
    getCollection(slug),
    listProducts(query, { collection: slug }),
  ]);
  if (!collection.ok && collection.status === 404) notFound(); // unpublished or unknown

  const title = collection.ok ? collection.data.name : "Collection";
  return (
    <ListingView
      title={title}
      eyebrow="Collection"
      description={collection.ok ? collection.data.description : null}
      breadcrumbs={[{ label: "Home", href: "/" }, { label: "Collections" }, { label: title }]}
      basePath={`/collections/${slug}`}
      query={query}
      result={result}
      options={content.catalog}
      emptyMessage={{
        title: "New styles are on their way",
        description: "This collection is being curated — check back soon.",
      }}
    />
  );
}
