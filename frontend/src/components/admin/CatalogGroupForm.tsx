"use client";

import { type FormEvent, useState } from "react";

import { Button } from "@/components/ui/Button";
import { Card, SelectInput, TextArea, TextInput, Toggle, adminStyles as styles } from "./Kit";
import { MediaField } from "./Pickers";

/** Shared editor for categories and collections (name, slug, image, SEO, visibility). */
export interface GroupFormState {
  name: string;
  slug: string;
  description: string;
  image_media_id: string | null;
  display_order: string;
  seo_title: string;
  seo_description: string;
  parent_id: string;
  is_active: boolean;
  custom_product_ordering: boolean;
  status: "draft" | "published";
}

export const emptyGroup = (): GroupFormState => ({
  name: "",
  slug: "",
  description: "",
  image_media_id: null,
  display_order: "0",
  seo_title: "",
  seo_description: "",
  parent_id: "",
  is_active: true,
  custom_product_ordering: false,
  status: "draft",
});

const orNull = (v: string) => (v.trim() === "" ? null : v.trim());

export function categoryPayload(f: GroupFormState) {
  return {
    name: f.name.trim(),
    slug: orNull(f.slug),
    description: orNull(f.description),
    parent_id: orNull(f.parent_id),
    image_media_id: f.image_media_id,
    is_active: f.is_active,
    display_order: Number.parseInt(f.display_order || "0", 10),
    custom_product_ordering: f.custom_product_ordering,
    seo_title: orNull(f.seo_title),
    seo_description: orNull(f.seo_description),
  };
}

export function collectionPayload(f: GroupFormState) {
  return {
    name: f.name.trim(),
    slug: orNull(f.slug),
    description: orNull(f.description),
    image_media_id: f.image_media_id,
    status: f.status,
    display_order: Number.parseInt(f.display_order || "0", 10),
    seo_title: orNull(f.seo_title),
    seo_description: orNull(f.seo_description),
  };
}

export function GroupForm({
  kind,
  initial,
  parents = [],
  submitLabel,
  pending,
  onSubmit,
}: {
  kind: "category" | "collection";
  initial: GroupFormState;
  parents?: { value: string; label: string }[];
  submitLabel: string;
  pending: boolean;
  onSubmit: (state: GroupFormState) => void;
}) {
  const [f, setF] = useState(initial);
  const [error, setError] = useState<string | null>(null);
  const set = <K extends keyof GroupFormState>(key: K, value: GroupFormState[K]) => setF((s) => ({ ...s, [key]: value }));

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!f.name.trim()) {
      setError("Name is required.");
      return;
    }
    setError(null);
    onSubmit(f);
  };

  return (
    <form onSubmit={submit} noValidate>
      <Card title="Details">
        <div className={styles.grid2}>
          <TextInput label="Name" value={f.name} onChange={(v) => set("name", v)} required maxLength={120} error={error} />
          <TextInput label="Slug" hint="Leave empty to generate from the name" value={f.slug} onChange={(v) => set("slug", v)} maxLength={160} />
        </div>
        <TextArea label="Description" value={f.description} onChange={(v) => set("description", v)} rows={3} maxLength={5000} />
        <div className={styles.grid2}>
          {kind === "category" ? (
            <SelectInput label="Parent category" value={f.parent_id} onChange={(v) => set("parent_id", v)} placeholder="None (top level)" options={parents} />
          ) : (
            <SelectInput
              label="Status"
              value={f.status}
              onChange={(v) => set("status", v as GroupFormState["status"])}
              options={[
                { value: "draft", label: "Draft (hidden)" },
                { value: "published", label: "Published" },
              ]}
            />
          )}
          <TextInput label="Display order" type="number" min={0} value={f.display_order} onChange={(v) => set("display_order", v)} hint="Lower numbers appear first" />
        </div>
        {kind === "category" && (
          <div className={styles.grid2}>
            <Toggle label="Visible on the storefront" checked={f.is_active} onChange={(v) => set("is_active", v)} />
            <Toggle label="Use custom product order" checked={f.custom_product_ordering} onChange={(v) => set("custom_product_ordering", v)} />
          </div>
        )}
        <MediaField
          label="Image"
          value={f.image_media_id}
          onChange={(id) => set("image_media_id", id)}
          purpose={kind === "category" ? "category_image" : "collection_image"}
          frame={kind}
        />
        <div className={styles.grid2}>
          <TextInput label="SEO title" value={f.seo_title} onChange={(v) => set("seo_title", v)} maxLength={70} />
          <TextInput label="SEO description" value={f.seo_description} onChange={(v) => set("seo_description", v)} maxLength={320} />
        </div>
        <div>
          <Button type="submit" loading={pending}>
            {submitLabel}
          </Button>
        </div>
      </Card>
    </form>
  );
}
