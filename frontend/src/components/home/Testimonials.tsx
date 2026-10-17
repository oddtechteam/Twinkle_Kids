import { Quote } from "lucide-react";

import { SectionHeading } from "@/components/ui/SectionHeading";
import type { TestimonialsSection } from "@/lib/content/types";
import styles from "./Testimonials.module.css";

/** Renders only real, admin-approved reviews; nothing is shown when none are configured. */
export function Testimonials({ section }: { section: TestimonialsSection }) {
  if (section.items.length === 0) return null;
  return (
    <section className="section" aria-labelledby={`${section.id}-title`}>
      <div className="container">
        <SectionHeading id={`${section.id}-title`} title={section.title} align="center" />
        <ul className={styles.grid}>
          {section.items.map((item) => (
            <li key={`${item.author}-${item.quote.slice(0, 24)}`} className={styles.card}>
              <Quote aria-hidden="true" size={28} className={styles.mark} />
              <blockquote className={styles.quote}>{item.quote}</blockquote>
              <p className={styles.author}>
                {item.author}
                {item.context && <span className={styles.context}>{item.context}</span>}
              </p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
