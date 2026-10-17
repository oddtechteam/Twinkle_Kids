"use client";

import Link from "next/link";
import { ExternalLink, Pencil, Plus, Send, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import {
  AdminPage,
  ConfirmDialog,
  ErrorState,
  LoadingState,
  Pill,
  SortableList,
  TextInput,
  Toggle,
  adminStyles as styles,
} from "@/components/admin/Kit";
import { SECTION_META, SECTION_TYPES } from "@/components/admin/sectionMeta";
import { Button, ButtonLink } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { useToast } from "@/components/ui/Toast";
import { adminApi, refreshStorefront } from "@/lib/admin/api";
import { useMutation, useResource } from "@/lib/admin/hooks";
import type { Section } from "@/lib/admin/types";
import { formatDateTime } from "@/lib/format";

export default function HomepageBuilderPage() {
  const router = useRouter();
  const toast = useToast();
  const home = useResource(adminApi.homepage, "homepage");
  const { run, pending } = useMutation();
  const [adding, setAdding] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [note, setNote] = useState("");
  const [deleting, setDeleting] = useState<Section | null>(null);

  if (home.loading && !home.data) return <LoadingState />;
  if (home.error && !home.data) return <ErrorState message={home.error} onRetry={home.reload} />;
  if (!home.data) return null;
  const { sections, publication } = home.data;

  const reorder = async (next: Section[]) => {
    const previous = sections;
    home.setData((d) => (d ? { ...d, sections: next } : d));
    const res = await run(() => adminApi.reorderSections(next.map((s) => s.id)), { success: "Order saved to draft" });
    if (res.ok) void home.reload();
    else home.setData((d) => (d ? { ...d, sections: previous } : d));
  };

  const publish = async () => {
    const res = await run(() => adminApi.publishHomepage(note.trim()), { success: "Homepage published" });
    if (!res.ok) return;
    setPublishing(false);
    setNote("");
    void home.reload();
    const refreshed = await refreshStorefront();
    if (!refreshed) {
      toast.show({
        tone: "warning",
        title: "Published, but the storefront cache wasn't refreshed",
        description: "The new homepage appears within a few minutes.",
      });
    }
  };

  return (
    <AdminPage
      title="Homepage builder"
      description="Changes here are saved as a draft. Customers see them only after you publish."
      breadcrumbs={[{ label: "Homepage" }]}
      actions={
        <>
          <ButtonLink href="/" target="_blank" variant="ghost" size="sm" iconStart={<ExternalLink aria-hidden="true" />}>
            View live
          </ButtonLink>
          <Button variant="outline" iconStart={<Plus aria-hidden="true" />} onClick={() => setAdding(true)}>
            Add section
          </Button>
          <Button iconStart={<Send aria-hidden="true" />} onClick={() => setPublishing(true)} disabled={!publication.has_unpublished_changes}>
            Publish
          </Button>
        </>
      }
    >
      <div className={styles.stack}>
        <div className={styles.notice} role="status">
          {publication.published_at ? <>Last published {formatDateTime(publication.published_at)}. </> : <>The homepage has never been published. </>}
          {publication.has_unpublished_changes ? <strong>There are unpublished changes.</strong> : "The live homepage matches this draft."}
        </div>
        {sections.length === 0 ? (
          <p className={styles.hint}>No sections yet — add the first one.</p>
        ) : (
          <SortableList
            label="Homepage sections"
            items={sections}
            getId={(s) => s.id}
            onReorder={(next) => void reorder(next)}
            renderItem={(s, index) => (
              <Link href={`/admin/homepage/${s.id}`} className={styles.cellTitle}>
                <span className={styles.muted}>{index + 1}.</span>
                <span>
                  <strong>{s.title || SECTION_META[s.section_type].label}</strong>
                  <span className={styles.hint}> · {SECTION_META[s.section_type].label}</span>
                </span>
                {!s.is_visible && <Pill tone="grey">Hidden</Pill>}
              </Link>
            )}
            renderActions={(s) => (
              <>
                <Toggle
                  label="Visible"
                  checked={s.is_visible}
                  onChange={async (value) => {
                    const res = await run(() => adminApi.setSectionVisibility(s.id, value), {
                      success: value ? "Section shown (draft)" : "Section hidden (draft)",
                    });
                    if (res.ok) void home.reload();
                  }}
                />
                <button type="button" className={styles.iconButton} onClick={() => router.push(`/admin/homepage/${s.id}`)} aria-label={`Edit ${s.title ?? "section"}`}>
                  <Pencil size={15} aria-hidden="true" />
                </button>
                <button type="button" className={`${styles.iconButton} ${styles.dangerIcon}`} onClick={() => setDeleting(s)} aria-label={`Delete ${s.title ?? "section"}`}>
                  <Trash2 size={15} aria-hidden="true" />
                </button>
              </>
            )}
          />
        )}
      </div>

      <Dialog open={adding} onClose={() => setAdding(false)} title="Add a section">
        <ul className={styles.list}>
          {SECTION_TYPES.map((type) => (
            <li key={type}>
              <Link href={`/admin/homepage/new?type=${type}`} className={styles.menuItem} style={{ display: "block" }}>
                <strong>{SECTION_META[type].label}</strong>
                <span className={styles.hint} style={{ display: "block" }}>
                  {SECTION_META[type].description}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </Dialog>

      <Dialog
        open={publishing}
        onClose={() => setPublishing(false)}
        title="Publish the homepage?"
        footer={
          <>
            <Button variant="ghost" onClick={() => setPublishing(false)}>
              Cancel
            </Button>
            <Button onClick={() => void publish()} loading={pending}>
              Publish now
            </Button>
          </>
        }
      >
        <div className={styles.stack}>
          <p className={styles.hint}>Visible sections in their current order replace the live homepage.</p>
          <TextInput label="Note (optional)" value={note} onChange={setNote} maxLength={200} placeholder="e.g. Festive banner" />
        </div>
      </Dialog>

      <ConfirmDialog
        open={deleting !== null}
        title="Delete this section?"
        message="It is removed from the draft. The live homepage keeps it until you publish again."
        confirmLabel="Delete section"
        destructive
        pending={pending}
        onClose={() => setDeleting(null)}
        onConfirm={async () => {
          if (!deleting) return;
          const res = await run(() => adminApi.deleteSection(deleting.id), { success: "Section deleted from draft" });
          setDeleting(null);
          if (res.ok) void home.reload();
        }}
      />
    </AdminPage>
  );
}
