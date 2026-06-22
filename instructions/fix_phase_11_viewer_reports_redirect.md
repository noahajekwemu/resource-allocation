Fix Phase 11 login next redirect for reports page.

Problem:
When an unauthenticated Viewer opens:
/forms/reports.html

The app redirects to login, but after successful login as viewer@subeb.local it redirects to:
/api/items

This is wrong.

Expected behavior:
If the user originally requested:
/forms/reports.html

then after successful login, and if the user's role is allowed to access that page, redirect back to:
/forms/reports.html

Requirements:

1. Update scripts/form_api.py.

2. Ensure /forms/reports.html is included in the form role permission map.

Allowed roles for reports.html:
- Admin
- Viewer
- Approver
- Store_Officer
- School_User

3. Ensure /forms/print_executive_summary.html is included if present.

Allowed roles for print_executive_summary.html:
- Admin
- Viewer
- Approver
- Store_Officer

School_User should receive 403.

4. Fix successful login redirect logic.

Priority order after successful login:

A. If a safe local next parameter exists:
   - Example: /forms/reports.html
   - Validate it is local and safe.
   - If it points to /forms/<filename>, check the logged-in user's role is allowed for that form.
   - If allowed, redirect to next.
   - If not allowed, return 403 or redirect to role default with a clear message.

B. If no valid next parameter exists:
   Use role default redirect:
   Admin -> /forms/approve_requisition.html
   Approver -> /forms/approve_requisition.html
   Store_Officer -> /forms/issue_stock.html
   School_User -> /forms/requisition_form.html
   Viewer -> /forms/reports.html

5. Change Viewer default redirect from /api/items to:
/forms/reports.html

6. Preserve safe redirect protection.

Reject unsafe next values:
- http://evil.com
- https://evil.com
- //evil.com

7. Preserve existing role protection:
- user_management.html is Admin only
- receive_stock.html is Admin and Store_Officer
- issue_stock.html is Admin and Store_Officer
- approve_requisition.html is Admin and Approver
- requisition_form.html is Admin and School_User
- reports.html is allowed to all authenticated roles

8. Add or update tests:
- Viewer opening /forms/reports.html when unauthenticated redirects to /login?next=/forms/reports.html
- Viewer login with next=/forms/reports.html redirects to /forms/reports.html
- Viewer default login without next redirects to /forms/reports.html
- Viewer still receives 403 for /forms/user_management.html
- Unsafe next URL is rejected
- School_User receives 403 for /forms/print_executive_summary.html
- Admin can access reports page

9. Ensure python -m pytest passes.
