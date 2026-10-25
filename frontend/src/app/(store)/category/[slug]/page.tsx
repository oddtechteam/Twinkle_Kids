import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { ListingSkeleton, ListingView } from "@/components/catalog/ListingView";
import { getCategory, getFacets, listProducts } from "@/lib/catalog/api";
import { buildFilterOptions } from "@/lib/catalog/filters";
import { parseListingQuery } from "@/lib/catalog/query";
import { getSiteContent } from "@/lib/content";

export async function generateMetadata({ params }: PageProps<"/category/[slug]">): Promise<Metadata> {
  const { slug } = await params;
  const result = await getCategory(slug);
  if (!result.ok) return { title: "Category" };
  const { category } = result.data;
  const description = category.seo_description ?? category.description ?? undefined;
  return {
    title: category.seo_title ?? category.name,
    description,
    alternates: { canonical: `/category/${category.slug}` },
    openGraph: {
      title: category.seo_title ?? category.name,
      description,
      url: `/category/${category.slug}`,
      images: category.image ? [{ url: category.image.url, width: category.image.width, height: category.image.height }] : undefined,
    },
  };
}

export default function CategoryPage({ params, searchParams }: PageProps<"/category/[slug]">) {
  return (
    <Suspense fallback={<ListingSkeleton />}>
      <CategoryListing params={params} searchParams={searchParams} />
    </Suspense>
  );
}

async function CategoryListing({ params, searchParams }: PageProps<"/category/[slug]">) {
  const [{ slug }, search, content] = await Promise.all([params, searchParams, getSiteContent()]);
  const query = parseListingQuery(search, content.defaultSort);
  const [detail, result, facets] = await Promise.all([
    getCategory(slug),
    listProducts(query, { category: slug }),
    getFacets({ category: slug, q: query.q }),
  ]);

  if (!detail.ok && detail.status === 404) notFound();

  const category = detail.ok ? detail.data.category : null;
  const title = category?.name ?? "Category";

  return (
    <ListingView
      title={title}
      eyebrow="Shop by category"
      description={category?.description}
      breadcrumbs={[
        { label: "Home", href: "/" },
        { label: "Shop", href: "/shop" },
        ...(detail.ok ? detail.data.breadcrumbs.map((c) => ({ label: c.name, href: `/category/${c.slug}` })) : []),
        { label: title },
      ]}
      basePath={`/category/${slug}`}
      query={query}
      result={result}
      options={buildFilterOptions(facets)}
      related={detail.ok ? detail.data.children.map((c) => ({ label: c.name, href: `/category/${c.slug}` })) : []}
    />
  );
}
