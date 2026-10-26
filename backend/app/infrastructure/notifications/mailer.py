"""Transactional email (password resets). SMTP in real environments; log-only in development.

The development mailer writes messages to the log so the reset flow can be exercised locally;
it is never selected in production, where a missing SMTP configuration disables sending (and
logs a warning) rather than leaking reset links into logs.
"""

import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import make_msgid

from app.application.ports import DeliveryReceipt

logger = logging.getLogger(__name__)


class SmtpMailer:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        sender: str,
        username: str | None = None,
        password: str | None = None,
        starttls: bool = True,
        timeout: float = 15.0,
    ) -> None:
        self._host = host
        self._port = port
        self._sender = sender
        self._username = username
        self._password = password
        self._starttls = starttls
        self._timeout = timeout

    def send(self, *, to: str, subject: str, text: str) -> DeliveryReceipt:
        message = EmailMessage()
        message["From"] = self._sender
        message["To"] = to
        message["Subject"] = subject
        message["Message-ID"] = make_msgid()
        message.set_content(text)
        try:
            with smtplib.SMTP(self._host, self._port, timeout=self._timeout) as smtp:
                if self._starttls:
                    smtp.starttls(context=ssl.create_default_context())
                if self._username and self._password:
                    smtp.login(self._username, self._password)
                refused = smtp.send_message(message)
        except (OSError, smtplib.SMTPException) as exc:
            # Never surface delivery details to the requester; the response is always generic.
            logger.error("Email delivery failed: %s", exc.__class__.__name__)
            return DeliveryReceipt(accepted=False, provider="smtp", error=exc.__class__.__name__)
        if refused:
            return DeliveryReceipt(accepted=False, provider="smtp", error="Recipient refused.")
        return DeliveryReceipt(accepted=True, provider="smtp", message_id=message["Message-ID"])


class DevelopmentLogMailer:
    """Development/test only: logs the message (including links) instead of sending it."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str, str]] = []

    def send(self, *, to: str, subject: str, text: str) -> DeliveryReceipt:
        self.sent.append((to, subject, text))
        logger.info("[dev mail] to=%s subject=%s\n%s", to, subject, text)
        # Logged locally, not delivered: never reported as sent.
        return DeliveryReceipt(accepted=False, provider="development-log", skipped=True)


class DisabledMailer:
    """Production without SMTP settings: nothing is sent (and nothing sensitive is logged)."""

    def send(self, *, to: str, subject: str, text: str) -> DeliveryReceipt:
        logger.warning("Email not sent (SMTP is not configured): %s", subject)
        return DeliveryReceipt(
            accepted=False, provider=None, skipped=True, error="SMTP is not configured."
        )
