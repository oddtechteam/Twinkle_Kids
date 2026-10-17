import Link from "next/link";
import { Mail, MapPin, MessageCircle, Phone } from "lucide-react";

import { Logo } from "@/components/brand/Logo";
import { Motif } from "@/components/ui/Motif";
import type { SiteContent } from "@/lib/content/types";
import styles from "./SiteFooter.module.css";

const SOCIAL_LABEL = {
  instagram: "Instagram",
  facebook: "Facebook",
  youtube: "YouTube",
  pinterest: "Pinterest",
} as const;

export function SiteFooter({ content }: { content: SiteContent }) {
  const { footer, contact, brand } = content;
  const hasContact = Boolean(contact.email || contact.phone || contact.whatsapp || contact.address);

  return (
    <footer className={styles.footer}>
      <div className={styles.wave} aria-hidden="true">
        <svg viewBox="0 0 1440 40" preserveAspectRatio="none">
          <path d="M0 40V18c120-14 240-18 360-8s240 22 360 18 240-22 360-26 240 6 360 16v22Z" />
        </svg>
      </div>

      <div className={`container ${styles.grid}`}>
        <div className={styles.brand}>
          <Logo tone="light" size="lg" name={brand.name} image={brand.logo} />
          <p className={styles.tagline}>
            <Motif size={12} /> {brand.tagline}
          </p>
          <p className={styles.blurb}>{footer.blurb}</p>
          {footer.social.length > 0 && (
            <ul className={styles.social} aria-label="Social media">
              {footer.social.map((item) => (
                <li key={item.network}>
                  <a href={item.href} className={styles.socialLink} target="_blank" rel="noopener noreferrer">
                    {SOCIAL_LABEL[item.network]}
                  </a>
                </li>
              ))}
            </ul>
          )}
        </div>

        {footer.columns.map((column) => (
          <nav key={column.title} aria-label={column.title} className={styles.column}>
            <h2 className={styles.heading}>{column.title}</h2>
            <ul className={styles.links}>
              {column.links.map((link) => (
                <li key={link.href}>
                  <Link href={link.href} className={styles.link}>
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        ))}

        {hasContact && (
          <div className={styles.column}>
            <h2 className={styles.heading}>Get in touch</h2>
            <ul className={styles.contact}>
              {contact.whatsapp && (
                <li>
                  <MessageCircle aria-hidden="true" size={18} />
                  <a href={`https://wa.me/${contact.whatsapp.replace(/\D/g, "")}`} className={styles.link}>
                    WhatsApp {contact.whatsapp}
                  </a>
                </li>
              )}
              {contact.phone && (
                <li>
                  <Phone aria-hidden="true" size={18} />
                  <a href={`tel:${contact.phone.replace(/\s/g, "")}`} className={styles.link}>
                    {contact.phone}
                  </a>
                </li>
              )}
              {contact.email && (
                <li>
                  <Mail aria-hidden="true" size={18} />
                  <a href={`mailto:${contact.email}`} className={styles.link}>
                    {contact.email}
                  </a>
                </li>
              )}
              {contact.address && (
                <li>
                  <MapPin aria-hidden="true" size={18} />
                  <span>{contact.address}</span>
                </li>
              )}
            </ul>
            {contact.hours && <p className={styles.hours}>{contact.hours}</p>}
          </div>
        )}
      </div>

      <div className={`container ${styles.bottom}`}>
        <p>© {brand.name}. All rights reserved.</p>
        <ul className={styles.policies}>
          {footer.policies.map((link) => (
            <li key={link.href}>
              <Link href={link.href} className={styles.link}>
                {link.label}
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </footer>
  );
}
