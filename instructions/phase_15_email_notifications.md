Phase 15 – Email notifications for approvals and stock issues.

Goal:
Add optional SMTP email notifications for key workflow events.

Files to create/update:
- scripts/email_utils.py
- scripts/form_api.py
- scripts/requisition_utils.py if present
- scripts/inventory_utils.py if present
- docs/EMAIL_NOTIFICATIONS.md
- tests/test_email_utils.py
- tests/test_requisition_approval.py
- tests/test_requisition_fulfillment.py

Environment variables:
EMAIL_NOTIFICATIONS_ENABLED
SMTP_HOST
SMTP_PORT
SMTP_USERNAME
SMTP_PASSWORD
SMTP_FROM_EMAIL
SMTP_USE_TLS

Events:
- Requisition submitted
- Requisition approved
- Requisition rejected
- Stock issued
- Requisition fulfilled
- Low stock warning if practical

Requirements:

1. If EMAIL_NOTIFICATIONS_ENABLED is not true, do not send email.

2. If SMTP configuration is missing, log warning and do not crash.

3. Never log SMTP_PASSWORD.

4. Email failures must not block the main transaction.

5. Add send_email(to, subject, body).

6. Add workflow-specific helpers:
- send_requisition_submitted_notification
- send_requisition_decision_notification
- send_stock_issued_notification
- send_low_stock_notification if practical

7. Determine recipients from Users sheet where practical:
- Admins
- Approvers
- Requesting school user
- Store officers

8. Add audit actions:
EMAIL_SENT
EMAIL_FAILED

9. Add tests using mocks; no real email should be sent during tests.

10. Add docs/EMAIL_NOTIFICATIONS.md explaining Render environment variables and how to enable later.

11. Preserve existing behavior and role checks.

12. Ensure python -m pytest passes.