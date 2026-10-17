import type { ReactNode } from "react";

import { type Crumb, Breadcrumbs } from "./Breadcrumbs";
import { EmptyState } from "./Feedback";
import styles from "./InfoPage.module.css";

/** Simple page frame for account, bag and content pages awaiting their backend features. */
export function InfoPage({
  breadcrumbs,
  title,
  description,
  icon,
  action,
}: {
  breadcrumbs: Crumb[];
  title: string;
  description: string;
  icon?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className={`container-narrow ${styles.page}`}>
      <Breadcrumbs items={breadcrumbs} />
      <EmptyState title={title} description={description} icon={icon} action={action} />
    </div>
  );
}
