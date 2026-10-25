import { Clock, Mail, MapPin, MessageCircle, Phone } from "lucide-react";
import type { ReactNode } from "react";

import { type Crumb, Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { buttonClass } from "@/components/ui/Button";
import { Accordion } from "@/components/ui/Form";
import type { PageBlock, PublishedPage } from "@/lib/content/pages";
import type { ContactDetails } from "@/lib/content/types";
import styles from "./CmsPage.module.css";

/**
 * A published CMS page (`website_pages`): structured blocks rendered as plain text — never raw
 * HTML. Used by /pages/[slug], /about and /contact.
 */
export function CmsPageArticle({
  title,
  blocks,
  breadcrumbs,
  children,
}: {
  title: string;
  blocks: PublishedPage["content"]["blocks"];
  breadcrumbs: Crumb[];
  children?: ReactNode;
}) {
  return (
    <article className={`container-narrow ${styles.page}`}>
      <Breadcrumbs items={breadcrumbs} />
      <h1 className={styles.title}>{title}</h1>
      {blocks && blocks.length > 0 && (
        <div className={styles.body}>
          {blocks.map((block, index) => (
            <Block key={index} block={block} />
          ))}
        </div>
      )}
      {children}
    </article>
  );
}

function Block({ block }: { block: PageBlock }) {
  switch (block.type) {
    case "heading":
      return block.level === 3 ? <h3 className={styles.h3}>{block.text}</h3> : <h2 className={styles.h2}>{block.text}</h2>;
    case "paragraph":
      return <p>{block.text}</p>;
    case "list":
      return block.ordered ? (
        <ol className={styles.list}>
          {block.items.map((item, i) => (
            <li key={i}>{item}</li>
          ))}
        </ol>
      ) : (
        <ul className={styles.list}>
          {block.items.map((item, i) => (
            <li key={i}>{item}</li>
          ))}
        </ul>
      );
    case "faq":
      return (
        <div className={styles.faq}>
          {block.items.map((item, i) => (
            <Accordion key={i} title={item.question}>
              <p>{item.answer}</p>
            </Accordion>
          ))}
        </div>
      );
    case "callout":
      return <p className={styles.callout}>{block.text}</p>;
    default:
      return null;
  }
}

export function hasContactDetails(contact: ContactDetails): boolean {
  return Boolean(contact.whatsapp || contact.phone || contact.email || contact.address || contact.hours);
}

/** Store contact details from settings (WhatsApp appears only when ordering is enabled). */
export function ContactCard({ contact, title = "Reach us" }: { contact: ContactDetails; title?: string }) {
  return (
    <section className={styles.contact} aria-labelledby="contact-card-title">
      <h2 id="contact-card-title" className={styles.h3}>
        {title}
      </h2>
      <div className={styles.contactActions}>
        {contact.whatsapp && (
          <a
            href={`https://wa.me/${contact.whatsapp.replace(/\D/g, "")}`}
            className={buttonClass({ variant: "primary" })}
            target="_blank"
            rel="noopener noreferrer"
          >
            <MessageCircle aria-hidden="true" size={18} /> WhatsApp us
          </a>
        )}
        {contact.phone && (
          <a href={`tel:${contact.phone.replace(/[^\d+]/g, "")}`} className={buttonClass({ variant: "outline" })}>
            <Phone aria-hidden="true" size={18} /> Call {contact.phone}
          </a>
        )}
        {contact.email && (
          <a href={`mailto:${contact.email}`} className={buttonClass({ variant: "outline" })}>
            <Mail aria-hidden="true" size={18} /> {contact.email}
          </a>
        )}
      </div>
      {(contact.address || contact.hours) && (
        <dl className={styles.contactFacts}>
          {contact.address && (
            <>
              <dt>
                <MapPin aria-hidden="true" size={16} /> Address
              </dt>
              <dd>{contact.address}</dd>
            </>
          )}
          {contact.hours && (
            <>
              <dt>
                <Clock aria-hidden="true" size={16} /> Hours
              </dt>
              <dd>{contact.hours}</dd>
            </>
          )}
        </dl>
      )}
    </section>
  );
}
