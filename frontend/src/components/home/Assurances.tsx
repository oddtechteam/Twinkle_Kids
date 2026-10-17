import { Icon } from "@/components/ui/Icon";
import type { AssurancesSection } from "@/lib/content/types";
import styles from "./Assurances.module.css";

export function Assurances({ section }: { section: AssurancesSection }) {
  if (section.items.length === 0) return null;
  const titleId = `${section.id}-title`;
  return (
    <section className={`section ${styles.section}`} aria-labelledby={section.title ? titleId : undefined}>
      <div className="container">
        {section.title && (
          <h2 id={titleId} className={styles.heading}>
            {section.title}
          </h2>
        )}
        <ul className={styles.grid}>
          {section.items.map((item) => (
            <li key={item.title} className={styles.item}>
              <span className={styles.icon}>
                <Icon name={item.icon} size={24} />
              </span>
              <h3 className={styles.title}>{item.title}</h3>
              <p className={styles.text}>{item.text}</p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
