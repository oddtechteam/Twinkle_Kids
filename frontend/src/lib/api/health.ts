import { apiFetch } from "./client";

export type ComponentState = "ok" | "down";

export interface ComponentHealth {
  name: string;
  state: ComponentState;
  latency_ms: number | null;
  detail: string | null;
}

export interface HealthReport {
  service: string;
  version: string;
  environment: string;
  status: ComponentState;
  components: ComponentHealth[];
}

export type HealthResult =
  | { reachable: true; report: HealthReport }
  | { reachable: false; error: string };

/** Readiness check; a 503 still carries a report describing which dependency is down. */
export async function getReadiness(): Promise<HealthResult> {
  try {
    const report = await apiFetch<HealthReport>("/health/ready", {
      cache: "no-store",
      acceptStatuses: [503],
    });
    return { reachable: true, report };
  } catch (error) {
    return { reachable: false, error: error instanceof Error ? error.message : "Unknown error" };
  }
}
