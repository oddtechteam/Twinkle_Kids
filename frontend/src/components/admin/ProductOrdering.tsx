"use client";

import { Plus, Trash2 } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { useMutation } from "@/lib/admin/hooks";
import type { AdminProductSummary } from "@/lib/admin/types";
import { formatMoney } from "@/lib/format";
import { Card, SortableList, StatusPill, adminStyles as styles } from "./Kit";
import { MediaThumb, ProductPicker } from "./Pickers";

/**
 * Edit an ordered product list (collection, category, homepage section). Changes stay local
 * until "Save order" persists the exact list through `onSave` — the context's own ordering.
 */
export function ProductOrdering({
  title,
  hint,
  initial,
  onSave,
  allowAddRemove = true,
}: {
  title: string;
  hint?: string;
  initial: AdminProductSummary[];
  onSave: (ids: string[]) => Promise<unknown>;
  allowAddRemove?: boolean;
}) {
  const [items, setItems] = useState(initial);
  const [dirty, setDirty] = useState(false);
  const [picking, setPicking] = useState(false);
  const { run, pending } = useMutation();

  const update = (next: AdminProductSummary[]) => {
    setItems(next);
    setDirty(true);
  };

  return (
    <Card
      title={title}
      hint={hint}
      actions={
        <>
          {allowAddRemove && (
            <Button size="sm" variant="soft" iconStart={<Plus aria-hidden="true" />} onClick={() => setPicking(true)}>
              Add products
            </Button>
          )}
          <Button
            size="sm"
            disabled={!dirty}
            loading={pending}
            onClick={async () => {
              const res = await run(() => onSave(items.map((p) => p.id)), { success: "Order saved" });
              if (res.ok) setDirty(false);
            }}
          >
            Save order
          </Button>
        </>
      }
    >
      {items.length === 0 ? (
        <p className={styles.hint}>No products yet.</p>
      ) : (
        <SortableList
          label={title}
          items={items}
          getId={(p) => p.id}
          onReorder={update}
          renderItem={(p, index) => (
            <span className={styles.cellTitle}>
              <span className={styles.muted}>{index + 1}.</span>
              <span className={styles.thumb}>
                <MediaThumb url={p.primary_image?.url} />
              </span>
              <span>
                {p.name}
                <span className={styles.hint}> · {formatMoney(p.price.selling_price)}</span>
              </span>
              <StatusPill status={p.status} />
            </span>
          )}
          renderActions={
            allowAddRemove
              ? (p) => (
                  <button
                    type="button"
                    className={`${styles.iconButton} ${styles.dangerIcon}`}
                    onClick={() => update(items.filter((x) => x.id !== p.id))}
                    aria-label={`Remove ${p.name}`}
                  >
                    <Trash2 size={15} aria-hidden="true" />
                  </button>
                )
              : undefined
          }
        />
      )}
      {dirty && <p className={styles.hint}>Unsaved changes — click “Save order”.</p>}
      <ProductPicker
        open={picking}
        onClose={() => setPicking(false)}
        excludeIds={items.map((p) => p.id)}
        onAdd={(added) => update([...items, ...added])}
      />
    </Card>
  );
}
