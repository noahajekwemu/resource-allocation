"""Optional SMTP email notifications for workflow events."""

import logging
import os
import smtplib
from email.message import EmailMessage
from typing import Any, Callable, Iterable

try:
    from scripts.audit_utils import write_audit_log
except (ImportError, ModuleNotFoundError):
    from audit_utils import write_audit_log


LOGGER = logging.getLogger(__name__)
TRUE_VALUES = {"1", "true", "yes", "on"}


def email_notifications_enabled() -> bool:
    return os.environ.get("EMAIL_NOTIFICATIONS_ENABLED", "").strip().lower() in TRUE_VALUES


def smtp_use_tls() -> bool:
    value = os.environ.get("SMTP_USE_TLS", "true").strip().lower()
    return value in TRUE_VALUES


def _smtp_config() -> dict[str, Any]:
    return {
        "host": os.environ.get("SMTP_HOST", "").strip(),
        "port": os.environ.get("SMTP_PORT", "").strip(),
        "username": os.environ.get("SMTP_USERNAME", "").strip(),
        "password": os.environ.get("SMTP_PASSWORD", ""),
        "from_email": os.environ.get("SMTP_FROM_EMAIL", "").strip(),
        "use_tls": smtp_use_tls(),
    }


def _missing_required_config(config: dict[str, Any]) -> list[str]:
    return [key for key in ("host", "port", "from_email") if not config.get(key)]


def _normalize_recipients(to: str | Iterable[str]) -> list[str]:
    if isinstance(to, str):
        candidates = [to]
    else:
        candidates = list(to)
    recipients = []
    for candidate in candidates:
        email = str(candidate or "").strip()
        if email and email not in recipients:
            recipients.append(email)
    return recipients


def _audit_email(
    action: str,
    recipients: list[str],
    subject: str,
    status: str,
    remarks: str = "",
    audit_writer: Callable[..., Any] | None = write_audit_log,
) -> None:
    if audit_writer is None:
        return
    try:
        audit_writer(
            action,
            "Email",
            subject,
            None,
            {"to": recipients, "subject": subject},
            status,
            remarks,
        )
    except Exception:
        LOGGER.exception("Failed to write email audit action %s", action)


def send_email(
    to: str | Iterable[str],
    subject: str,
    body: str,
    audit_writer: Callable[..., Any] | None = write_audit_log,
) -> bool:
    """Send one email message when notifications are enabled."""
    if not email_notifications_enabled():
        return False

    recipients = _normalize_recipients(to)
    if not recipients:
        LOGGER.warning("Email notifications enabled but no recipients were provided.")
        return False

    config = _smtp_config()
    missing = _missing_required_config(config)
    if missing:
        LOGGER.warning(
            "Email notifications enabled but SMTP configuration is missing: %s",
            ", ".join(missing),
        )
        _audit_email(
            "EMAIL_FAILED",
            recipients,
            subject,
            "Failed",
            "Missing SMTP configuration: " + ", ".join(missing),
            audit_writer,
        )
        return False

    message = EmailMessage()
    message["From"] = config["from_email"]
    message["To"] = ", ".join(recipients)
    message["Subject"] = subject
    message.set_content(body)

    try:
        with smtplib.SMTP(config["host"], int(config["port"]), timeout=20) as smtp:
            if config["use_tls"]:
                smtp.starttls()
            if config["username"] and config["password"]:
                smtp.login(config["username"], config["password"])
            smtp.send_message(message)
    except Exception as exc:
        LOGGER.warning("Email delivery failed for subject %r: %s", subject, exc)
        _audit_email("EMAIL_FAILED", recipients, subject, "Failed", str(exc), audit_writer)
        return False

    _audit_email("EMAIL_SENT", recipients, subject, "Success", "", audit_writer)
    return True


def recipient_emails(
    users: Iterable[dict[str, Any]],
    roles: set[str] | None = None,
    school_id: str | None = None,
) -> list[str]:
    recipients = []
    normalized_roles = {role.lower() for role in roles or set()}
    requested_school = str(school_id or "").strip()
    for user in users:
        role = str(user.get("Role", "")).strip()
        email = str(user.get("Email", "")).strip()
        active = str(user.get("Active", "true")).strip().lower()
        user_school = str(user.get("School_ID", "")).strip()
        if not email or active in {"false", "0", "no"}:
            continue
        if normalized_roles and role.lower() not in normalized_roles:
            continue
        if requested_school and user_school != requested_school:
            continue
        if email not in recipients:
            recipients.append(email)
    return recipients


def send_requisition_submitted_notification(
    requisition: dict[str, Any],
    users: Iterable[dict[str, Any]],
) -> bool:
    requisition_id = str(requisition.get("requisition_id") or requisition.get("Requisition_ID") or "")
    school_id = str(requisition.get("School_ID") or requisition.get("school_id") or "")
    recipients = recipient_emails(users, {"Admin", "Approver"})
    subject = f"New requisition submitted: {requisition_id}"
    body = (
        f"A new requisition has been submitted.\n\n"
        f"Requisition ID: {requisition_id}\n"
        f"School ID: {school_id}\n"
        "Status: Pending"
    )
    return send_email(recipients, subject, body)


def send_requisition_decision_notification(
    requisition: dict[str, Any],
    users: Iterable[dict[str, Any]],
    status: str,
    remarks: str = "",
) -> bool:
    requisition_id = str(requisition.get("requisition_id") or requisition.get("Requisition_ID") or "")
    school_id = str(requisition.get("School_ID") or requisition.get("school_id") or "")
    recipients = recipient_emails(users, {"School_User"}, school_id=school_id)
    subject = f"Requisition {status.lower()}: {requisition_id}"
    body = (
        f"Your requisition has been {status.lower()}.\n\n"
        f"Requisition ID: {requisition_id}\n"
        f"Status: {status}\n"
        f"Remarks: {remarks or 'None'}"
    )
    return send_email(recipients, subject, body)


def send_stock_issued_notification(
    transaction: dict[str, Any],
    users: Iterable[dict[str, Any]],
) -> bool:
    transaction_id = str(transaction.get("transaction_id") or transaction.get("Transaction_ID") or "")
    requisition_id = str(transaction.get("requisition_id") or transaction.get("Requisition_ID") or "")
    school_id = str(transaction.get("School_ID") or transaction.get("school_id") or "")
    recipients = recipient_emails(users, {"Admin", "Store_Officer"})
    recipients.extend(
        email for email in recipient_emails(users, {"School_User"}, school_id=school_id)
        if email not in recipients
    )
    subject = f"Stock issued: {transaction_id}"
    body = (
        f"Stock has been issued.\n\n"
        f"Transaction ID: {transaction_id}\n"
        f"Requisition ID: {requisition_id or 'Not linked'}"
    )
    return send_email(recipients, subject, body)


def send_low_stock_notification(
    item: dict[str, Any],
    users: Iterable[dict[str, Any]],
) -> bool:
    recipients = recipient_emails(users, {"Admin", "Store_Officer"})
    item_name = str(item.get("Item_Name") or item.get("Item_ID") or "Unknown item")
    subject = f"Low stock warning: {item_name}"
    body = (
        f"Low stock warning for {item_name}.\n\n"
        f"Current stock: {item.get('Current_Stock', 'Unknown')}\n"
        f"Minimum stock: {item.get('Minimum_Stock', item.get('Reorder_Level', 'Unknown'))}"
    )
    return send_email(recipients, subject, body)
