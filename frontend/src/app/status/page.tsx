import type { Metadata } from "next";
import { Suspense } from "react";

import { StatusBadge } from "@/components/status/StatusBadge";
import { getReadiness } from "@/lib/api/health";
import styles from "./page.module.css";

export const metadata: Metadata = {
  title: "System status",
  robots: { index: false, follow: false },
};

export default function StatusPage() {
  return (
    <section className={`container ${styles.page}`} aria-labelledby="status-title">
      <h1 id="status-title" className={styles.title}>
        System status
      </h1>
      <ul className={styles.list}>
        <li className={styles.row}>
          <span>Storefront (Next.js)</span>
          <StatusBadge ok />
        </li>
        <Suspense
          fallback={
            <li className={styles.row} aria-busy="true">
              <span>Checking API…</span>
            </li>
          }
        >
          <BackendStatus />
        </Suspense>
      </ul>
    </section>
  );
}

async function BackendStatus() {
  const result = await getReadiness();

  if (!result.reachable) {
    return (
      <li className={styles.row}>
        <span>
          API <small className={styles.detail}>could not be reached</small>
        </span>
        <StatusBadge ok={false} />
      </li>
    );
  }

  const { report } = result;
  return (
    <>
      <li className={styles.row}>
        <span>
          API{" "}
          <small className={styles.detail}>
            v{report.version} · {report.environment}
          </small>
        </span>
        <StatusBadge ok={report.status === "ok"} />
      </li>
      {report.components.map((component) => (
        <li key={component.name} className={styles.row}>
          <span className={styles.component}>
            {component.name}{" "}
            <small className={styles.detail}>
              {component.detail}
              {component.latency_ms !== null && ` · ${component.latency_ms} ms`}
            </small>
          </span>
          <StatusBadge ok={component.state === "ok"} />
        </li>
      ))}
    </>
  );
}
