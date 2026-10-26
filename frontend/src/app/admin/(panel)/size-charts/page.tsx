"use client";

import { Pencil, Plus, Trash2 } from "lucide-react";
import { type FormEvent, useState } from "react";

import {
  AdminPage,
  type Column,
  ConfirmDialog,
  DataTable,
  ErrorState,
  LoadingState,
  SelectInput,
  TextArea,
  TextInput,
  adminStyles as styles,
} from "@/components/admin/Kit";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { adminApi } from "@/lib/admin/api";
import { useMutation, useResource } from "@/lib/admin/hooks";
import type { SizeChart } from "@/lib/admin/types";

function ChartDialog({ chart, onClose, onSaved }: { chart: SizeChart | null; onClose: () => void; onSaved: () => void }) {
  const [name, setName] = useState(chart?.name ?? "");
  const [slug, setSlug] = useState(chart?.slug ?? "");
  const [description, setDescription] = useState(chart?.description ?? "");
  const [unit, setUnit] = useState<"cm" | "in">(chart?.chart.unit ?? "cm");
  const [columns, setColumns] = useState<string[]>(chart?.chart.columns ?? ["Size", "Age", "Chest", "Length"]);
  const [rows, setRows] = useState<string[][]>(chart?.chart.rows ?? [["", "", "", ""]]);
  const { run, pending } = useMutation();

  const setCell = (r: number, c: number, value: string) => setRows((list) => list.map((row, i) => (i === r ? row.map((cell, j) => (j === c ? value : cell)) : row)));
  const addColumn = () => {
    setColumns((c) => [...c, ""]);
    setRows((list) => list.map((row) => [...row, ""]));
  };
  const removeColumn = (index: number) => {
    setColumns((c) => c.filter((_, i) => i !== index));
    setRows((list) => list.map((row) => row.filter((_, i) => i !== index)));
  };

  const valid = name.trim() && columns.length >= 2 && columns.every((c) => c.trim()) && rows.length >= 1;

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!valid) return;
    const body = {
      name: name.trim(),
      slug: slug.trim() || null,
      description: description.trim() || null,
      chart: { unit, columns: columns.map((c) => c.trim()), rows: rows.map((r) => r.map((c) => c.trim())) },
    };
    const res = await run(() => (chart ? adminApi.updateSizeChart(chart.id, body) : adminApi.createSizeChart(body).then(() => undefined)), {
      success: chart ? "Size chart saved" : "Size chart added",
    });
    if (res.ok) onSaved();
  };

  return (
    <Dialog open onClose={onClose} title={chart ? "Edit size chart" : "New size chart"}>
      <form onSubmit={submit} className={styles.stack} noValidate>
        <div className={styles.grid2}>
          <TextInput label="Name" placeholder="e.g. Girls' frocks" value={name} onChange={setName} maxLength={120} required />
          <TextInput label="Slug" hint="Optional" value={slug} onChange={setSlug} maxLength={160} />
        </div>
        <TextArea label="Notes" hint="e.g. how to measure" value={description} onChange={setDescription} maxLength={2000} rows={2} />
        <SelectInput
          label="Unit"
          value={unit}
          onChange={(v) => setUnit(v === "in" ? "in" : "cm")}
          options={[
            { value: "cm", label: "Centimetres" },
            { value: "in", label: "Inches" },
          ]}
        />
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                {columns.map((c, i) => (
                  <th key={i}>
                    <span style={{ display: "flex", gap: "var(--space-1)" }}>
                      <input className={styles.input} value={c} maxLength={30} aria-label={`Column ${i + 1} name`} onChange={(e) => setColumns((list) => list.map((x, j) => (j === i ? e.target.value : x)))} />
                      <button type="button" className={`${styles.iconButton} ${styles.dangerIcon}`} onClick={() => removeColumn(i)} disabled={columns.length <= 2} aria-label="Remove column">
                        <Trash2 size={14} aria-hidden="true" />
                      </button>
                    </span>
                  </th>
                ))}
                <th />
              </tr>
            </thead>
            <tbody>
              {rows.map((row, r) => (
                <tr key={r}>
                  {row.map((cell, c) => (
                    <td key={c}>
                      <input className={styles.input} value={cell} maxLength={30} aria-label={`Row ${r + 1}, ${columns[c] || `column ${c + 1}`}`} onChange={(e) => setCell(r, c, e.target.value)} />
                    </td>
                  ))}
                  <td>
                    <button type="button" className={`${styles.iconButton} ${styles.dangerIcon}`} onClick={() => setRows((list) => list.filter((_, i) => i !== r))} disabled={rows.length <= 1} aria-label="Remove row">
                      <Trash2 size={14} aria-hidden="true" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className={styles.actions}>
          <Button size="sm" variant="soft" iconStart={<Plus aria-hidden="true" />} onClick={() => setRows((list) => [...list, columns.map(() => "")])} disabled={rows.length >= 30}>
            Add row
          </Button>
          <Button size="sm" variant="soft" iconStart={<Plus aria-hidden="true" />} onClick={addColumn} disabled={columns.length >= 8}>
            Add column
          </Button>
        </div>
        <Button type="submit" loading={pending} disabled={!valid}>
          {chart ? "Save size chart" : "Add size chart"}
        </Button>
      </form>
    </Dialog>
  );
}

export default function SizeChartsPage() {
  const charts = useResource(adminApi.sizeCharts, "size-charts");
  const { run, pending } = useMutation();
  const [editing, setEditing] = useState<SizeChart | null | "new">(null);
  const [deleting, setDeleting] = useState<SizeChart | null>(null);

  const columns: Column<SizeChart>[] = [
    { header: "Size chart", render: (c) => <strong>{c.name}</strong> },
    { header: "Columns", render: (c) => (c.chart.columns ?? []).join(", ") },
    { header: "Rows", render: (c) => c.chart.rows?.length ?? 0 },
    {
      header: "Actions",
      align: "end",
      render: (c) => (
        <div className={styles.rowActions}>
          <button type="button" className={styles.iconButton} onClick={() => setEditing(c)} aria-label={`Edit ${c.name}`}>
            <Pencil size={15} aria-hidden="true" />
          </button>
          <button type="button" className={`${styles.iconButton} ${styles.dangerIcon}`} onClick={() => setDeleting(c)} aria-label={`Delete ${c.name}`}>
            <Trash2 size={15} aria-hidden="true" />
          </button>
        </div>
      ),
    },
  ];

  return (
    <AdminPage
      title="Size charts"
      description="Attach a size chart to products from the product editor."
      breadcrumbs={[{ label: "Size charts" }]}
      actions={
        <Button iconStart={<Plus aria-hidden="true" />} onClick={() => setEditing("new")}>
          New size chart
        </Button>
      }
    >
      {charts.error && <ErrorState message={charts.error} onRetry={charts.reload} />}
      {charts.loading && !charts.data && <LoadingState label="Loading size charts…" />}
      {charts.data && <DataTable columns={columns} rows={charts.data} rowKey={(c) => c.id} empty={<p className={styles.hint}>No size charts yet.</p>} />}
      {editing !== null && (
        <ChartDialog
          key={editing === "new" ? "new" : editing.id}
          chart={editing === "new" ? null : editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            void charts.reload();
          }}
        />
      )}
      <ConfirmDialog
        open={deleting !== null}
        title={`Delete “${deleting?.name ?? ""}”?`}
        message="Products using this chart will no longer show a size guide."
        confirmLabel="Delete size chart"
        destructive
        pending={pending}
        onClose={() => setDeleting(null)}
        onConfirm={async () => {
          if (!deleting) return;
          const res = await run(() => adminApi.deleteSizeChart(deleting.id), { success: "Size chart deleted" });
          setDeleting(null);
          if (res.ok) void charts.reload();
        }}
      />
    </AdminPage>
  );
}
