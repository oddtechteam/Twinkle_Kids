"use client";

import { useParams } from "next/navigation";
import { Suspense } from "react";

import { AdminPage, ErrorState, LoadingState, Pill } from "@/components/admin/Kit";
import { SectionEditor } from "@/components/admin/SectionEditor";
import { SECTION_META } from "@/components/admin/sectionMeta";
import { adminApi } from "@/lib/admin/api";
import { useResource } from "@/lib/admin/hooks";

function EditSection() {
  const { id } = useParams<{ id: string }>();
  const section = useResource(() => adminApi.section(id), id);

  if (section.loading && !section.data) return <LoadingState />;
  if (section.error) return <ErrorState message={section.error} onRetry={section.reload} />;
  const s = section.data;
  if (!s) return null;
  const label = SECTION_META[s.section_type].label;

  return (
    <AdminPage
      title={s.title || label}
      description={label}
      breadcrumbs={[{ label: "Homepage", href: "/admin/homepage" }, { label: s.title || label }]}
      actions={!s.is_visible ? <Pill tone="grey">Hidden</Pill> : undefined}
    >
      <SectionEditor key={`${s.id}-${s.selection_mode}`} type={s.section_type} section={s} onSaved={() => void section.reload()} />
    </AdminPage>
  );
}

export default function EditSectionPage() {
  return (
    <Suspense fallback={<LoadingState />}>
      <EditSection />
    </Suspense>
  );
}
