"""Notification abstraction: one place that sends customer messages and records the outcome.

A delivery is recorded as `sent` only when the provider accepted it (SMTP said OK). The local
development mailer and an unconfigured channel are recorded as `skipped`. WhatsApp Business API
delivery is a future integration: until a provider is configured nothing is sent, and a normal
click-to-chat link is never treated as a delivered or received message. Message bodies are not
stored — they can contain one-time links.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID, uuid4

from app.application.dto.catalog import Page
from app.application.ports import DeliveryReceipt, Mailer
from app.domain.enums import NotificationChannel, NotificationStatus


@dataclass(frozen=True, slots=True)
class NotificationRecord:
    id: UUID
    channel: NotificationChannel
    template: str
    recipient: str
    subject: str | None
    status: NotificationStatus
    provider: str | None
    provider_message_id: str | None
    error: str | None
    entity_type: str | None
    entity_id: str | None
    created_at: datetime | None = None


class NotificationLog(Protocol):
    def record(self, entry: NotificationRecord) -> None: ...

    def list(
        self, *, status: NotificationStatus | None, page: int, page_size: int
    ) -> Page[NotificationRecord]: ...


class WhatsAppBusinessSender(Protocol):
    """Future WhatsApp Business API provider (template messages). Not click-to-chat."""

    @property
    def configured(self) -> bool: ...

    def send_template(
        self, *, to: str, template: str, variables: dict[str, str]
    ) -> DeliveryReceipt: ...


class NotConfiguredWhatsApp:
    configured = False

    def send_template(
        self, *, to: str, template: str, variables: dict[str, str]
    ) -> DeliveryReceipt:
        return DeliveryReceipt(
            accepted=False,
            provider=None,
            skipped=True,
            error="WhatsApp Business API is not configured.",
        )


def _mask(recipient: str) -> str:
    """Keep the log useful without storing full contact details."""
    if "@" in recipient:
        name, _, domain = recipient.partition("@")
        return f"{name[:2]}***@{domain}"
    digits = "".join(c for c in recipient if c.isdigit())
    return f"***{digits[-4:]}" if digits else "***"


class Notifier:
    def __init__(
        self,
        *,
        mailer: Mailer,
        log: NotificationLog,
        whatsapp: WhatsAppBusinessSender | None = None,
    ) -> None:
        self._mailer = mailer
        self._log = log
        self._whatsapp = whatsapp or NotConfiguredWhatsApp()

    def email(
        self,
        *,
        template: str,
        to: str,
        subject: str,
        text: str,
        entity_type: str | None = None,
        entity_id: str | None = None,
    ) -> NotificationStatus:
        if not to:
            receipt = DeliveryReceipt(
                accepted=False, provider=None, skipped=True, error="No email address."
            )
        else:
            try:
                receipt = self._mailer.send(to=to, subject=subject, text=text)
            except Exception as exc:
                receipt = DeliveryReceipt(
                    accepted=False, provider=None, error=exc.__class__.__name__
                )
        return self._record(
            NotificationChannel.EMAIL, template, to, subject, receipt, entity_type, entity_id
        )

    def whatsapp(
        self,
        *,
        template: str,
        to: str,
        variables: dict[str, str],
        entity_type: str | None = None,
        entity_id: str | None = None,
    ) -> NotificationStatus:
        receipt = self._whatsapp.send_template(to=to, template=template, variables=variables)
        return self._record(
            NotificationChannel.WHATSAPP, template, to, None, receipt, entity_type, entity_id
        )

    def _record(
        self,
        channel: NotificationChannel,
        template: str,
        to: str,
        subject: str | None,
        receipt: DeliveryReceipt,
        entity_type: str | None,
        entity_id: str | None,
    ) -> NotificationStatus:
        status = (
            NotificationStatus.SENT
            if receipt.accepted
            else NotificationStatus.SKIPPED
            if receipt.skipped
            else NotificationStatus.FAILED
        )
        self._log.record(
            NotificationRecord(
                id=uuid4(),
                channel=channel,
                template=template,
                recipient=_mask(to),
                subject=subject[:200] if subject else None,
                status=status,
                provider=receipt.provider,
                provider_message_id=receipt.message_id,
                error=(receipt.error or None) and receipt.error[:300],
                entity_type=entity_type,
                entity_id=entity_id,
            )
        )
        return status

    def history(self, *, status: NotificationStatus | None, page: int) -> Page[NotificationRecord]:
        return self._log.list(status=status, page=max(1, page), page_size=50)
