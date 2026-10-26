import type { ReactNode } from "react";

import { AdminShell } from "@/components/admin/AdminShell";

/** The admin panel is a client-rendered, session-gated app that loads its data after
 *  navigation, so it is not expected to navigate instantly (opts out of dev validation). */
export const instant = false;

export default function AdminPanelLayout({ children }: { children: ReactNode }) {
  return <AdminShell>{children}</AdminShell>;
}
