from __future__ import annotations

import mimetypes
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path


def _split_recipients(value: str) -> list[str]:
    return [item.strip() for item in value.replace(";", ",").split(",") if item.strip()]


class EmailSender:
    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        username: str | None = None,
        password: str | None = None,
        sender: str | None = None,
        use_tls: bool | None = None,
    ) -> None:
        self.host = host or os.getenv("SMTP_HOST", "").strip()
        self.port = port or int(os.getenv("SMTP_PORT", "587") or "587")
        self.username = username or os.getenv("SMTP_USER", "").strip()
        self.password = password or os.getenv("SMTP_PASSWORD", "").strip()
        self.sender = sender or os.getenv("SMTP_FROM", "").strip() or self.username
        self.use_tls = use_tls if use_tls is not None else os.getenv("SMTP_USE_TLS", "true").strip().lower() in {"1", "true", "yes", "y"}

        if not self.host or not self.sender:
            raise ValueError("缺少 SMTP_HOST 或 SMTP_FROM/SMTP_USER，无法发送邮件。")

    def send(
        self,
        *,
        subject: str,
        body: str,
        to: list[str] | str,
        cc: list[str] | str | None = None,
        attachments: list[Path] | None = None,
    ) -> None:
        to_list = _split_recipients(to) if isinstance(to, str) else to
        cc_list = _split_recipients(cc or "") if isinstance(cc, str) or cc is None else cc
        recipients = [*to_list, *cc_list]
        if not recipients:
            raise ValueError("邮件收件人为空。")

        message = EmailMessage()
        message["From"] = self.sender
        message["To"] = ", ".join(to_list)
        if cc_list:
            message["Cc"] = ", ".join(cc_list)
        message["Subject"] = subject
        message.set_content(body)

        for path in attachments or []:
            if not path or not path.exists():
                continue
            content_type, _encoding = mimetypes.guess_type(path.name)
            maintype, subtype = (content_type or "application/octet-stream").split("/", 1)
            message.add_attachment(
                path.read_bytes(),
                maintype=maintype,
                subtype=subtype,
                filename=path.name,
            )

        with smtplib.SMTP(self.host, self.port, timeout=60) as smtp:
            if self.use_tls:
                smtp.starttls()
            if self.username and self.password:
                smtp.login(self.username, self.password)
            smtp.send_message(message, to_addrs=recipients)


def send_report_email(
    *,
    subject: str,
    body: str,
    attachments: list[Path] | None = None,
    to: str | None = None,
    cc: str | None = None,
) -> None:
    EmailSender().send(
        subject=subject,
        body=body,
        to=to or os.getenv("REPORT_EMAIL_TO", ""),
        cc=cc or os.getenv("REPORT_EMAIL_CC", ""),
        attachments=attachments,
    )
