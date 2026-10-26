"use client";

import { Copy, MessageCircle } from "lucide-react";
import { useCallback, useState } from "react";

import { Button, buttonClass } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { useToast } from "@/components/ui/Toast";
import type { WhatsAppLink } from "@/lib/api/types";
import { bagErrorMessage, startWhatsAppRequest } from "@/lib/bag/api";
import styles from "./WhatsAppHandoff.module.css";

/**
 * Order-on-WhatsApp hand-off. The backend records a request and returns a wa.me link; we try
 * to open it, and always show the reference plus a retry link, because opening WhatsApp is not
 * proof that anything was sent — the customer still has to review and send the message.
 */
export function useWhatsAppOrder() {
  const toast = useToast();
  const [link, setLink] = useState<WhatsAppLink | null>(null);
  const [opening, setOpening] = useState(false);

  const start = useCallback(
    async (items: { variantId: string; quantity: number }[]) => {
      // Open the tab inside the click so pop-up blockers allow it, then point it at WhatsApp.
      const tab = window.open("", "_blank");
      setOpening(true);
      try {
        const created = await startWhatsAppRequest(items);
        setLink(created); // shown even if the tab opened: the customer must still press Send
        if (tab) {
          tab.opener = null;
          tab.location.href = created.url;
        }
      } catch (error) {
        tab?.close();
        toast.show({ tone: "warning", title: "Couldn't start your WhatsApp order", description: bagErrorMessage(error) });
      } finally {
        setOpening(false);
      }
    },
    [toast],
  );

  const dialog = link ? <HandoffDialog link={link} onClose={() => setLink(null)} /> : null;
  return { start, opening, dialog };
}

function HandoffDialog({ link, onClose }: { link: WhatsAppLink; onClose: () => void }) {
  const toast = useToast();
  return (
    <Dialog open onClose={onClose} title="Send your order on WhatsApp">
      <div className={styles.body}>
        <p className={styles.reference}>
          Request reference <strong>{link.reference}</strong>
        </p>
        <ol className={styles.steps}>
          <li>WhatsApp should now be open with your order details filled in.</li>
          <li>
            <strong>Review the message and tap Send.</strong> We only receive your request once you send it.
          </li>
          <li>We&apos;ll reply to confirm availability, delivery and payment. Nothing is charged or reserved until then.</li>
        </ol>
        <p className={styles.muted}>Didn&apos;t open, or closed it by mistake? Open it again below.</p>
        <div className={styles.actions}>
          <a href={link.url} target="_blank" rel="noopener noreferrer" className={buttonClass({ variant: "primary" })}>
            <MessageCircle aria-hidden="true" size={18} /> Open WhatsApp
          </a>
          <Button
            variant="outline"
            iconStart={<Copy aria-hidden="true" size={16} />}
            onClick={async () => {
              try {
                await navigator.clipboard.writeText(link.message);
                toast.show({ title: "Message copied", description: "Paste it into a WhatsApp chat with us." });
              } catch {
                toast.show({ tone: "warning", title: "Couldn't copy", description: "Please use “Open WhatsApp” instead." });
              }
            }}
          >
            Copy message
          </Button>
        </div>
      </div>
    </Dialog>
  );
}
