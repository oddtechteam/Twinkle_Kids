"use client";

import { BadgeCheck, Star } from "lucide-react";
import { useState } from "react";

import { AdminPage, ErrorState, LoadingState, Pill, adminStyles as styles } from "@/components/admin/Kit";
import { Button } from "@/components/ui/Button";
import { useMutation, useResource } from "@/lib/admin/hooks";
import { type ModerationReview, type ReviewStatus, opsApi } from "@/lib/admin/operations";
import { formatDateTime } from "@/lib/format";

const TABS: { value: ReviewStatus; label: string }[] = [
  { value: "pending", label: "Awaiting moderation" },
  { value: "approved", label: "Published" },
  { value: "rejected", label: "Hidden" },
];

export default function ReviewsPage() {
  const [status, setStatus] = useState<ReviewStatus>("pending");
  const [page, setPage] = useState(1);
  const list = useResource(() => opsApi.reviews({ status, page }), `${status}-${page}`);
  const { run, pending } = useMutation();

  async function moderate(review: ModerationReview, next: "approved" | "rejected") {
    const res = await run(() => opsApi.moderate(review.id, next, null), { success: next === "approved" ? "Review published" : "Review hidden" });
    if (res.ok) void list.reload();
  }

  return (
    <AdminPage
      title="Reviews"
      description="Every review waits here until you publish it. “Verified purchase” is set automatically only when the reviewer has a real order for the product."
    >
      <div className={styles.tabs} role="group" aria-label="Review status">
        {TABS.map((tab) => (
          <button
            key={tab.value}
            type="button"
            className={styles.tab}
            aria-pressed={status === tab.value}
            onClick={() => {
              setStatus(tab.value);
              setPage(1);
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>
      {list.error && <ErrorState message={list.error} onRetry={list.reload} />}
      {list.loading && !list.data && <LoadingState label="Loading reviews…" />}
      {list.data && list.data.items.length === 0 && <p className={styles.hint}>Nothing here.</p>}
      {list.data && list.data.items.length > 0 && (
        <ul className={styles.stack}>
          {list.data.items.map((r) => (
            <li key={r.id} className={styles.card}>
              <div className={styles.cardHeader}>
                <div>
                  <p className={styles.cardTitle}>
                    <span aria-label={`${r.rating} out of 5 stars`}>
                      {Array.from({ length: 5 }, (_, i) => (
                        <Star key={i} size={14} aria-hidden="true" fill={i < r.rating ? "currentColor" : "none"} />
                      ))}
                    </span>{" "}
                    {r.title}
                  </p>
                  <p className={styles.cardHint}>
                    {r.product_name} · {r.author_name ?? "Customer"} ({r.author_email ?? "no email"}) · {formatDateTime(r.created_at)}
                  </p>
                </div>
                {r.is_verified_purchase ? (
                  <Pill tone="green">
                    <BadgeCheck size={12} aria-hidden="true" /> Verified purchase
                  </Pill>
                ) : (
                  <Pill tone="grey">Not verified</Pill>
                )}
              </div>
              {r.body && <p>{r.body}</p>}
              {r.images.length > 0 && (
                <div className={styles.rowActions}>
                  {r.images.map((img) => (
                    // eslint-disable-next-line @next/next/no-img-element -- short-lived private links
                    <img key={img.media_asset_id} src={img.url} alt={img.alt_text ?? "Customer photo"} width={96} height={96} style={{ objectFit: "cover", borderRadius: 8 }} />
                  ))}
                </div>
              )}
              {r.moderation_note && <p className={styles.hint}>Note: {r.moderation_note}</p>}
              <div className={styles.rowActions}>
                {r.status !== "approved" && (
                  <Button size="sm" onClick={() => void moderate(r, "approved")} disabled={pending}>
                    Publish
                  </Button>
                )}
                {r.status !== "rejected" && (
                  <Button size="sm" variant="outline" onClick={() => void moderate(r, "rejected")} disabled={pending}>
                    Hide
                  </Button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
      {list.data && list.data.pages > 1 && (
        <div className={styles.pager}>
          <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage(page - 1)}>
            Previous
          </Button>
          <span className={styles.hint}>
            Page {list.data.page} of {list.data.pages}
          </span>
          <Button size="sm" variant="outline" disabled={page >= list.data.pages} onClick={() => setPage(page + 1)}>
            Next
          </Button>
        </div>
      )}
    </AdminPage>
  );
}
