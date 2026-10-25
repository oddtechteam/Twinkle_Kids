import type { Metadata } from "next";
import { Suspense } from "react";

import { ListingSkeleton, ListingView } from "@/components/catalog/ListingView";
import { getFacets, listCategories, listCollections, listProducts } from "@/lib/catalog/api";
import { buildFilterOptions } from "@/lib/catalog/filters";
import { parseListingQuery } from "@/lib/catalog/query";
import { getSiteContent } from "@/lib/content";

export async function generateMetadata(): Promise<Metadata> {
  const { brand } = await getSiteContent();
  return {
    title: "Shop all styles",
    description: `Browse the full ${brand.name} collection of children's clothing.`,
    alternates: { canonical: "/shop" },
  };
}

export default function ShopPage({ searchParams }: PageProps<"/shop">) {
  return (
    <Suspense fallback={<ListingSkeleton />}>
      <ShopListing searchParams={searchParams} />
    </Suspense>
  );
}

async function ShopListing({ searchParams }: Pick<PageProps<"/shop">, "searchParams">) {
  const [params, content] = await Promise.all([searchParams, getSiteContent()]);
  const query = parseListingQuery(params, content.defaultSort);
  const [result, facets, categories, collections] = await Promise.all([
    listProducts(query),
    getFacets({ category: query.category ?? undefined, collection: query.collection ?? undefined, q: query.q }),
    listCategories(),
    listCollections(),
  ]);
  const isNew = query.sort === "newest";

  return (
    <ListingView
      title={isNew ? "New arrivals" : "Shop all styles"}
      eyebrow={isNew ? "Just in" : "The collection"}
      description={
        isNew
          ? "The latest additions to the Twinkle Kids boutique."
          : "Everyday outfits, festive looks and special occasion styles."
      }
      breadcrumbs={[{ label: "Home", href: "/" }, { label: isNew ? "New arrivals" : "Shop all" }]}
      basePath="/shop"
      query={query}
      result={result}
      options={buildFilterOptions(facets, { categories, collections })}
    />
  );
}
