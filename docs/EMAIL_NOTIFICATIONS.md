# Email Notifications

Email notifications are optional and disabled by default. The application only sends mail when `EMAIL_NOTIFICATIONS_ENABLED` is set to `true`.

## Render Environment Variables

Configure these variables in Render before enabling notifications:

- `EMAIL_NOTIFICATIONS_ENABLED`: set to `true` to send email.
- `SMTP_HOST`: SMTP server host.
- `SMTP_PORT`: SMTP server port, for example `587`.
- `SMTP_USERNAME`: SMTP username, if required by the provider.
- `SMTP_PASSWORD`: SMTP password or app password.
- `SMTP_FROM_EMAIL`: sender address used in messages.
- `SMTP_USE_TLS`: set to `true` for STARTTLS, or `false` if the SMTP provider does not use it.

Do not commit SMTP credentials to the repository. `SMTP_PASSWORD` is never logged by the notification utility.

## Events

The system can notify users for:

- Requisition submitted
- Requisition approved
- Requisition rejected
- Stock issued
- Requisition fulfilled
- Low stock warning through the reusable helper

Recipients are selected from the `Users` sheet where practical:

- Admins and Approvers receive new requisition notifications.
- School users for the matching `School_ID` receive approval, rejection, and fulfillment notifications.
- Admins and Store Officers receive stock issue notifications.

## Failure Behavior

Email delivery is best effort. If email is disabled, missing SMTP configuration, or SMTP delivery fails, the main requisition or inventory transaction still completes.

When delivery is attempted, audit rows use:

- `EMAIL_SENT`
- `EMAIL_FAILED`
