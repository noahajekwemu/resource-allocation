Phase 11 navigation cleanup and role-aware UI.

Current issues:
1. Public dashboard still shows "Secure Login" even when user is logged into Flask.
This is expected because the dashboard is static, but the label should be clearer.

2. Secured pages show links that some roles cannot access.
For example Viewer clicks User Management, Submit Requisition, Receive Stock, Issue Stock, Approve Requests and receives 403.
Backend 403 is correct, but UI should hide or disable links the role cannot access.

3. API Status is visible as a navigation item on secured pages.
It is useful on the public dashboard, but confusing inside secured Flask pages.

Requirements:

1. Add endpoint:
GET /api/me

If logged in, return:
{
  "authenticated": true,
  "user_id": "...",
  "email": "...",
  "full_name": "...",
  "role": "...",
  "school_id": "..."
}

If not logged in, return:
{
  "authenticated": false
}

Do not expose Password_Hash.

2. Protect /api/me appropriately:
- It may return unauthenticated false without login.
- It must never expose secret fields.

3. Update secured form pages:
- reports.html
- user_management.html
- approve_requisition.html
- receive_stock.html
- issue_stock.html
- requisition_form.html
- print_executive_summary.html if applicable

Add role-aware navigation behavior:
- Fetch /api/me on page load.
- Display current user full name/email and role if available.
- Hide links the current role cannot access.

Role navigation rules:

Admin:
- Dashboard
- Reports
- User Management
- Submit Requisition
- Receive Stock
- Issue Stock
- Approve Requests
- Logout

Viewer:
- Dashboard
- Reports
- Logout

Approver:
- Dashboard
- Reports
- Approve Requests
- Logout

Store_Officer:
- Dashboard
- Reports
- Receive Stock
- Issue Stock
- Logout

School_User:
- Dashboard
- Reports
- Submit Requisition
- Logout

4. Remove API Status link from secured form navigation.
Keep API Status only on the public dashboard.

5. Update public dashboard navigation label:
Change "Secure Login" to:
"Secure Portal"

The link should still go to:
https://resource-allocation-api.onrender.com/login

6. On reports.html:
- Keep report cards visible if allowed.
- Hide or disable Audit Report for non-Admin.
- Hide Stock Report for School_User.
- Show a small notice:
"Access is based on your assigned system role."

7. Preserve backend 403 protections.
Do not rely only on front-end hiding.

8. Preserve:
- /health
- /login
- /logout
- /forms/<filename>
- all report endpoints
- all stock/requisition endpoints
- audit logging

9. Add tests for:
- /api/me unauthenticated response
- /api/me authenticated response does not expose Password_Hash
- Viewer cannot access user management
- Viewer can access reports page
- Admin can access user management
- protected backend routes still return 403 for unauthorized roles

10. Ensure python -m pytest passes.
