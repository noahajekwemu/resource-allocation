Fix successful login default redirect.

Problem:
Login succeeds for admin@subeb.local, but after POST /login the browser redirects to:
/api/items

This is wrong because /api/items is a JSON API endpoint.

Requirements:

1. Update scripts/form_api.py.

2. After successful login, redirect users by role:

Admin:
  /forms/approve_requisition.html

Approver:
  /forms/approve_requisition.html

Store_Officer:
  /forms/issue_stock.html

School_User:
  /forms/requisition_form.html

Viewer:
  /api/items

3. Preserve support for a safe local next parameter.

Example:
If the login URL is:
/login?next=/forms/issue_stock.html

and the user has permission, redirect to that page after login.

4. Do not allow unsafe external redirects such as:
http://evil.com
https://evil.com
//evil.com

5. Do not default Admin users to /api/items.

6. Add or update tests verifying:
- Admin login redirects to /forms/approve_requisition.html
- Approver login redirects to /forms/approve_requisition.html
- Store_Officer login redirects to /forms/issue_stock.html
- School_User login redirects to /forms/requisition_form.html
- Viewer login may redirect to /api/items
- Unsafe next URLs are rejected

7. Preserve:
- existing session behavior
- audit logging
- role protection
- /api/items
- /api/schools
- /api/warehouses
- /forms/<filename> serving

"@ | Set-Content instructions\fix_login_default_redirect.md
