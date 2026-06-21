Phase 10.1 – Production hardening for Flask API.

Goal:
Harden the deployed Flask API for production use on Render while preserving local development compatibility.

Files to update:
- scripts/form_api.py
- scripts/security_utils.py if needed
- scripts/audit_utils.py if needed
- requirements.txt if needed
- tests/test_security_utils.py
- tests/test_role_permissions.py

Requirements:

1. Add environment-aware configuration.

Use environment variable:
APP_ENV

Accepted values:
- development
- production

Default:
development

2. FORM_API_SECRET_KEY behavior:

In development:
- If FORM_API_SECRET_KEY is missing, allow fallback secret.
- Log a clear warning.

In production:
- If FORM_API_SECRET_KEY is missing, raise RuntimeError during app startup.
- Do not use insecure fallback.

3. Flask debug mode:

When running scripts/form_api.py directly:
- debug=True only if APP_ENV is development.
- debug=False if APP_ENV is production.

4. Secure session settings:

Set:
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"

If APP_ENV is production:
SESSION_COOKIE_SECURE = True

If APP_ENV is development:
SESSION_COOKIE_SECURE = False

5. Add session timeout.

Use:
PERMANENT_SESSION_LIFETIME = 60 minutes

After successful login:
session.permanent = True

6. Add simple no-cache headers for protected pages and API responses.

For protected form pages and authenticated API responses, add headers:
Cache-Control: no-store

7. Improve error pages.

Add friendly handlers for:
- 403
- 404
- 500

Return clear messages and avoid exposing stack traces in production.

8. Preserve existing routes:
- /health
- /login
- /logout
- /forms/<filename>
- /api/items
- /api/schools
- /api/warehouses
- requisition endpoints
- approval endpoints
- receive stock endpoints
- issue stock endpoints

9. Preserve role-based access:
- Admin
- Approver
- Store_Officer
- School_User
- Viewer

10. Preserve audit logging:
- LOGIN
- FAILED_LOGIN
- LOGOUT
- stock actions
- requisition actions

11. Add tests for:
- production requires FORM_API_SECRET_KEY
- development fallback still works
- session cookie config
- successful login makes session permanent
- protected forms return no-store header
- 403 handler works
- 404 handler works

12. Ensure python -m pytest passes.
