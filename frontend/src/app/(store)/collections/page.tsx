import type { Metadata } from "next";
import { Suspense } from "react";

import { FeaturedCollections } from "@/components/home/FeaturedCollections";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { ButtonLink } from "@/components/ui/Button";
import { EmptyState, Skeleton } from "@/components/ui/Feedback";
import { listCollections } from "@/lib/catalog/api";
import { collectionTiles } from "@/lib/content/cms";

/** Index of every published collection (GET /collections), in the admin's display order. */
export const metadata: Metadata = {
  title: "Collections",
  description: "Explore curated Twinkle Kids collections for every little moment and celebration.",
  alternates: { canonical: "/collections" },
};

export default function CollectionsPage() {
  return (
    <>
      <div className="container">
        <Breadcrumbs items={[{ label: "Home", href: "/" }, { label: "Collections" }]} />
        <h1 className="visually-hidden">Collections</h1>
      </div>
      <Suspense fallback={<CollectionsSkeleton />}>
        <CollectionsIndex />
      </Suspense>
    </>
  );
}

async function CollectionsIndex() {
  const result = await listCollections();
  if (!result.ok) {
    return (
      <div className="container section">
        <EmptyState
          tone="error"
          title="Collections are unavailable right now"
          description="Please try again in a moment."
          action={<ButtonLink href="/shop">Shop all styles</ButtonLink>}
        />
      </div>
    );
  }
  if (result.data.length === 0) {
    return (
      <div className="container section">
        <EmptyState
          title="New collections are on their way"
          description="Our team is curating them now — in the meantime, explore every style in the shop."
          action={<ButtonLink href="/shop">Shop all styles</ButtonLink>}
        />
      </div>
    );
  }
  return (
    <FeaturedCollections
      section={{
        id: "collections-index",
        type: "featured_collections",
        visible: true,
        eyebrow: "Curated for little moments",
        title: "Our collections",
        items: collectionTiles(result.data),
      }}
    />
  );
}

function CollectionsSkeleton() {
  return (
    <div className="container section">
      <Skeleton height="28rem" radius="var(--radius-xl)" />
    </div>
  );
}
