"use client";

import { ExternalLink, Plus, Trash2 } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";

import {
  AdminPage,
  Card,
  ConfirmDialog,
  ErrorState,
  LoadingState,
  SelectInput,
  SortableList,
  StatusPill,
  TextArea,
  TextInput,
  Toggle,
  adminStyles as styles,
} from "@/components/admin/Kit";
import { Button, ButtonLink } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { adminApi, refreshStorefront } from "@/lib/admin/api";
import { useMutation, useResource } from "@/lib/admin/hooks";
import type { PageBlock, PublishStatus, WebsitePage } from "@/lib/admin/types";

type Keyed = { key: string; block: PageBlock };
let seq = 0;
const keyed = (block: PageBlock): Keyed => ({ key: `b${++seq}`, block });

const BLOCK_TYPES: { type: PageBlock["type"]; label: string; make: () => PageBlock }[] = [
  { type: "heading", label: "Heading", make: () => ({ type: "heading", text: "", level: 2 }) },
  { type: "paragraph", label: "Paragraph", make: () => ({ type: "paragraph", text: "" }) },
  { type: "list", label: "List", make: () => ({ type: "list", ordered: false, items: [""] }) },
  { type: "faq", label: "FAQ", make: () => ({ type: "faq", items: [{ question: "", answer: "" }] }) },
  { type: "callout", label: "Callout", make: () => ({ type: "callout", text: "" }) },
];

function BlockFields({ block, onChange }: { block: PageBlock; onChange: (b: PageBlock) => void }) {
  switch (block.type) {
    case "heading":
      return (
        <div className={styles.grid2}>
          <TextInput label="Heading" value={block.text} onChange={(text) => onChange({ ...block, text })} maxLength={160} />
          <SelectInput
            label="Size"
            value={String(block.level)}
            onChange={(v) => onChange({ ...block, level: v === "3" ? 3 : 2 })}
            options={[
              { value: "2", label: "Section heading" },
              { value: "3", label: "Sub-heading" },
            ]}
          />
        </div>
      );
    case "paragraph":
      return <TextArea label="Paragraph" value={block.text} onChange={(text) => onChange({ ...block, text })} maxLength={4000} rows={5} />;
    case "callout":
      return <TextArea label="Callout" value={block.text} onChange={(text) => onChange({ ...block, text })} maxLength={600} rows={3} />;
    case "list":
      return (
        <>
          <Toggle label="Numbered list" checked={block.ordered} onChange={(ordered) => onChange({ ...block, ordered })} />
          <TextArea
            label="Items (one per line)"
            value={block.items.join("\n")}
            onChange={(v) => onChange({ ...block, items: v.split("\n") })}
            rows={Math.max(3, block.items.length)}
          />
        </>
      );
    case "faq":
      return (
        <div className={styles.stack}>
          {block.items.map((item, i) => (
            <div key={i} className={styles.blockEditor}>
              <div className={styles.blockHeader}>
                <span>Question {i + 1}</span>
                <button
                  type="button"
                  className={`${styles.iconButton} ${styles.dangerIcon}`}
                  onClick={() => onChange({ ...block, items: block.items.filter((_, j) => j !== i) })}
                  aria-label="Remove question"
                  disabled={block.items.length === 1}
                >
                  <Trash2 size={15} aria-hidden="true" />
                </button>
              </div>
              <TextInput
                label="Question"
                value={item.question}
                onChange={(question) => onChange({ ...block, items: block.items.map((x, j) => (j === i ? { ...x, question } : x)) })}
                maxLength={160}
              />
              <TextArea
                label="Answer"
                value={item.answer}
                onChange={(answer) => onChange({ ...block, items: block.items.map((x, j) => (j === i ? { ...x, answer } : x)) })}
                maxLength={1000}
                rows={3}
              />
            </div>
          ))}
          <div>
            <Button size="sm" variant="soft" iconStart={<Plus aria-hidden="true" />} onClick={() => onChange({ ...block, items: [...block.items, { question: "", answer: "" }] })}>
              Add question
            </Button>
          </div>
        </div>
      );
  }
}

/** Trim text and drop empty list lines so the strict backend schema accepts the content. */
function cleanBlock(block: PageBlock): PageBlock {
  switch (block.type) {
    case "list":
      return { ...block, items: block.items.map((i) => i.trim()).filter(Boolean) };
    case "faq":
      return { ...block, items: block.items.map((i) => ({ question: i.question.trim(), answer: i.answer.trim() })) };
    default:
      return { ...block, text: block.text.trim() };
  }
}

function Editor({ page, onSaved }: { page: WebsitePage; onSaved: () => void }) {
  const router = useRouter();
  const toast = useToast();
  const { run, pending } = useMutation();
  const [title, setTitle] = useState(page.title);
  const [slug, setSlug] = useState(page.slug);
  const [seoTitle, setSeoTitle] = useState(page.seo_title ?? "");
  const [seoDescription, setSeoDescription] = useState(page.seo_description ?? "");
  const [blocks, setBlocks] = useState<Keyed[]>(() => (page.content.blocks ?? []).map(keyed));
  const [confirmDelete, setConfirmDelete] = useState(false);

  const save = async (status: PublishStatus) => {
    const body = {
      title: title.trim(),
      slug: slug.trim() || null,
      status,
      content: { blocks: blocks.map((b) => cleanBlock(b.block)) },
      seo_title: seoTitle.trim() || null,
      seo_description: seoDescription.trim() || null,
    };
    const res = await run(() => adminApi.updatePage(page.id, body), {
      success: status === "published" ? (page.status === "published" ? "Published changes" : "Page published") : page.status === "published" ? "Page unpublished (now a draft)" : "Draft saved",
    });
    if (!res.ok) return;
    onSaved();
    if ((status === "published" || page.status === "published") && !(await refreshStorefront())) {
      toast.show({ tone: "warning", title: "Saved, but the storefront cache wasn't refreshed", description: "Changes appear within a few minutes." });
    }
  };

  return (
    <AdminPage
      title={page.title}
      breadcrumbs={[{ label: "Pages", href: "/admin/pages" }, { label: page.title }]}
      actions={
        <>
          <StatusPill status={page.status} />
          {page.status === "published" && (
            <ButtonLink href={`/pages/${page.slug}`} target="_blank" size="sm" variant="ghost" iconStart={<ExternalLink aria-hidden="true" />}>
              View
            </ButtonLink>
          )}
        </>
      }
    >
      <div className={styles.twoCol}>
        <div className={styles.stack}>
          <Card title="Page">
            <div className={styles.grid2}>
              <TextInput label="Title" value={title} onChange={setTitle} maxLength={160} required />
              <TextInput label="Slug" hint={`/pages/${slug || "…"}`} value={slug} onChange={setSlug} maxLength={160} />
            </div>
          </Card>
          <Card title="Content" hint="Plain text blocks — formatting is applied by the storefront design.">
            {blocks.length === 0 && <p className={styles.hint}>No content yet. Add a block below.</p>}
            {blocks.length > 0 && (
              <SortableList
                label="Content blocks"
                items={blocks}
                getId={(b) => b.key}
                onReorder={setBlocks}
                renderItem={(b) => (
                  <div className={styles.stack} style={{ gap: "var(--space-2)" }}>
                    <span className={styles.label}>{BLOCK_TYPES.find((t) => t.type === b.block.type)?.label}</span>
                    <BlockFields block={b.block} onChange={(block) => setBlocks((list) => list.map((x) => (x.key === b.key ? { ...x, block } : x)))} />
                  </div>
                )}
                renderActions={(b) => (
                  <button
                    type="button"
                    className={`${styles.iconButton} ${styles.dangerIcon}`}
                    onClick={() => setBlocks((list) => list.filter((x) => x.key !== b.key))}
                    aria-label="Remove block"
                  >
                    <Trash2 size={15} aria-hidden="true" />
                  </button>
                )}
              />
            )}
            <div className={styles.actions}>
              {BLOCK_TYPES.map((t) => (
                <Button key={t.type} size="sm" variant="soft" iconStart={<Plus aria-hidden="true" />} onClick={() => setBlocks((list) => [...list, keyed(t.make())])}>
                  {t.label}
                </Button>
              ))}
            </div>
          </Card>
          <Card title="Search engine listing">
            <TextInput label="SEO title" value={seoTitle} onChange={setSeoTitle} maxLength={70} />
            <TextArea label="SEO description" value={seoDescription} onChange={setSeoDescription} maxLength={320} rows={3} />
          </Card>
        </div>
        <div className={styles.stack}>
          <Card title="Publishing">
            <p className={styles.hint}>
              {page.status === "published"
                ? "This page is live. “Save draft” takes it offline until you publish again."
                : "Drafts are never shown on the storefront."}
            </p>
            <Button fullWidth loading={pending} onClick={() => void save("published")} disabled={!title.trim()}>
              {page.status === "published" ? "Publish changes" : "Publish"}
            </Button>
            <Button fullWidth variant="outline" onClick={() => void save("draft")} disabled={pending || !title.trim()}>
              {page.status === "published" ? "Unpublish & save draft" : "Save draft"}
            </Button>
            <Button fullWidth variant="ghost" iconStart={<Trash2 aria-hidden="true" />} onClick={() => setConfirmDelete(true)}>
              Delete page
            </Button>
          </Card>
        </div>
      </div>
      <ConfirmDialog
        open={confirmDelete}
        title="Delete this page?"
        message="Menu links pointing to it are removed too. This cannot be undone."
        confirmLabel="Delete page"
        destructive
        pending={pending}
        onClose={() => setConfirmDelete(false)}
        onConfirm={async () => {
          const res = await run(() => adminApi.deletePage(page.id), { success: "Page deleted" });
          setConfirmDelete(false);
          if (res.ok) {
            if (page.status === "published") void refreshStorefront();
            router.replace("/admin/pages");
          }
        }}
      />
    </AdminPage>
  );
}

export function PageEditor() {
  const { id } = useParams<{ id: string }>();
  const page = useResource(() => adminApi.page(id), id);
  if (page.loading && !page.data) return <LoadingState />;
  if (page.error) return <ErrorState message={page.error} onRetry={page.reload} />;
  if (!page.data) return null;
  return <Editor key={`${page.data.id}-${page.data.updated_at}`} page={page.data} onSaved={() => void page.reload()} />;
}
