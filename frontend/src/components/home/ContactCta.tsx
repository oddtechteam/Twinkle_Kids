import { Mail, MessageCircle, Phone } from "lucide-react";

import { buttonClass } from "@/components/ui/Button";
import { Motif } from "@/components/ui/Motif";
import type { ContactDetails, ContactSection } from "@/lib/content/types";
import styles from "./ContactCta.module.css";

/** Contact prompt — rendered only when real contact details are configured in settings. */
export function ContactCta({ section, contact }: { section: ContactSection; contact: ContactDetails }) {
  return (
    <section className="section" aria-labelledby={`${section.id}-title`}>
      <div className="container">
        <div className={styles.card}>
          <Motif size={22} twinkle className={styles.star} />
          <h2 id={`${section.id}-title`} className={styles.title}>
            {section.title}
          </h2>
          {section.body && <p className={styles.body}>{section.body}</p>}
          <div className={styles.actions}>
            {contact.whatsapp && section.showWhatsapp !== false && (
              <a
                href={`https://wa.me/${contact.whatsapp.replace(/\D/g, "")}`}
                className={buttonClass({ variant: "primary", size: "lg" })}
                target="_blank"
                rel="noopener noreferrer"
              >
                <MessageCircle aria-hidden="true" size={20} /> Message on WhatsApp
              </a>
            )}
            {contact.phone && section.showPhone !== false && (
              <a href={`tel:${contact.phone.replace(/\s/g, "")}`} className={buttonClass({ variant: "outline", size: "lg" })}>
                <Phone aria-hidden="true" size={20} /> Call us
              </a>
            )}
            {contact.email && section.showEmail !== false && (
              <a href={`mailto:${contact.email}`} className={buttonClass({ variant: "outline", size: "lg" })}>
                <Mail aria-hidden="true" size={20} /> Email us
              </a>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
