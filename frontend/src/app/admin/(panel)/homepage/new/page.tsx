"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { AdminPage, ErrorState, LoadingState } from "@/components/admin/Kit";
import { SectionEditor } from "@/components/admin/SectionEditor";
import { SECTION_META } from "@/components/admin/sectionMeta";
import type { SectionType } from "@/lib/admin/types";

function NewSection() {
  const type = useSearchParams().get("type") as SectionType | null;
  if (!type || !(type in SECTION_META)) return <ErrorState message="Unknown section type." />;
  return (
    <AdminPage
      title={`New ${SECTION_META[type].label.toLowerCase()}`}
      breadcrumbs={[{ label: "Homepage", href: "/admin/homepage" }, { label: "New section" }]}
    >
      <SectionEditor key={type} type={type} />
    </AdminPage>
  );
}

export default function NewSectionPage() {
  return (
    <Suspense fallback={<LoadingState />}>
      <NewSection />
    </Suspense>
  );
}
