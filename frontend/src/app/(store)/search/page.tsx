import type { Metadata } from "next";
import { Search } from "lucide-react";
import { Suspense } from "react";

import { ListingSkeleton, ListingView } from "@/components/catalog/ListingView";
import { Button } from "@/components/ui/Button";
import { TextField } from "@/components/ui/Form";
import { getFacets, listProducts } from "@/lib/catalog/api";
import { buildFilterOptions } from "@/lib/catalog/filters";
import { parseListingQuery } from "@/lib/catalog/query";
import { getSiteContent } from "@/lib/content";
import styles from "./page.module.css";

export const metadata: Metadata = {
  title: "Search",
  robots: { index: false, follow: true },
};

export default function SearchPage({ searchParams }: PageProps<"/search">) {
  return (
    <Suspense fallback={<ListingSkeleton />}>
      <SearchResults searchParams={searchParams} />
    </Suspense>
  );
}

function SearchForm({ defaultValue }: { defaultValue?: string }) {
  // Plain GET form: works before JavaScript loads and keeps the query in the URL.
  return (
    <form action="/search" role="search" className={styles.form}>
      <TextField
        label="Search products"
        hideLabel
        type="search"
        name="q"
        defaultValue={defaultValue}
        placeholder="Search dresses, tees, party wear…"
        icon={<Search aria-hidden="true" size={20} />}
        maxLength={100}
        className={styles.field}
      />
      <Button type="submit">Search</Button>
    </form>
  );
}

async function SearchResults({ searchParams }: Pick<PageProps<"/search">, "searchParams">) {
  const [params, content] = await Promise.all([searchParams, getSiteContent()]);
  const query = parseListingQuery(params, content.defaultSort);

  if (!query.q) {
    return (
      <section className={`container-narrow ${styles.blank}`}>
        <h1 className={styles.title}>What are you looking for?</h1>
        <p className={styles.lede}>Search by style, occasion or product name.</p>
        <SearchForm />
      </section>
    );
  }

  const [result, facets] = await Promise.all([listProducts(query), getFacets({ q: query.q })]);
  return (
    <ListingView
      title={`Results for “${query.q}”`}
      eyebrow="Search"
      breadcrumbs={[{ label: "Home", href: "/" }, { label: "Search" }]}
      basePath="/search"
      query={query}
      result={result}
      options={buildFilterOptions(facets)}
      headerExtra={<SearchForm defaultValue={query.q} />}
      emptyMessage={{
        title: `No styles match “${query.q}”`,
        description: "Try a broader word like “dress” or “tee”, or browse the full collection.",
      }}
    />
  );
}
