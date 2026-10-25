import { LoadingState } from "@/components/admin/Kit";

/** Route-level fallback while an admin screen is being prepared (inside the admin shell). */
export default function AdminLoading() {
  return <LoadingState />;
}
