import { ListingSkeleton } from "@/components/catalog/ListingView";

/** Same skeleton as the page's own Suspense fallback, so nothing jumps when data streams in. */
export default function Loading() {
  return <ListingSkeleton />;
}
