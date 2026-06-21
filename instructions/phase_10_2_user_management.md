Phase 10.2 – Add Admin User Management UI.

Goal:
Create an Admin-only user management page for managing system users stored in the Users worksheet.

Files to update/create:
- forms/user_management.html
- scripts/form_api.py
- scripts/security_utils.py
- scripts/audit_utils.py
- dashboard/index.html
- dashboard/js/dashboard.js
- dashboard/css/styles.css
- tests/test_role_permissions.py
- tests/test_security_utils.py

User worksheet columns:
User_ID
Full_Name
Email
Role
School_ID
Password_Hash
Active
Created_At

Allowed roles:
Admin
Approver
Store_Officer
School_User
Viewer

Requirements:

1. Create new form page:
forms/user_management.html

Page title:
User Management

2. Add dashboard navigation link:
User Management

It should point to:
https://resource-allocation-api.onrender.com/forms/user_management.html

3. Protect page:
Only Admin can access:
/forms/user_management.html

All other roles must receive 403.
Unauthenticated users must redirect to login with next parameter.

4. Add API endpoint:
GET /api/users

Admin only.

Return users without Password_Hash.

Fields returned:
User_ID
Full_Name
Email
Role
School_ID
Active
Created_At

5. Add API endpoint:
POST /api/users

Admin only.

Accept JSON:
{
  "Full_Name": "...",
  "Email": "...",
  "Role": "...",
  "School_ID": "...",
  "Password": "...",
  "Active": true
}

Validate:
- Full_Name required
- Email required
- Email must be unique
- Role must be one of allowed roles
- Password required
- School_ID required only when Role is School_User
- Active defaults to true

Create:
- new User_ID like USR006, USR007, etc.
- Password_Hash using existing hash_password function
- Created_At current timestamp/date

Never store plain password.

6. Add API endpoint:
PATCH /api/users/<user_id>

Admin only.

Allow updating:
- Full_Name
- Role
- School_ID
- Active

Do not allow updating:
- User_ID
- Email
- Password_Hash through this endpoint

7. Add API endpoint:
POST /api/users/<user_id>/reset-password

Admin only.

Accept JSON:
{
  "Password": "..."
}

Hash and update Password_Hash.

8. Add audit actions:
CREATE_USER
UPDATE_USER
RESET_USER_PASSWORD
DEACTIVATE_USER
ACTIVATE_USER

Audit rows must include:
- acting admin
- target User_ID
- before_state JSON
- after_state JSON
- success/failure status

9. User Management page UI:

Show table:
- User_ID
- Full Name
- Email
- Role
- School_ID
- Active
- Created_At
- Actions

Actions:
- Edit user
- Activate/Deactivate
- Reset password

Add create-user form:
- Full Name
- Email
- Role dropdown
- School dropdown
- Password
- Active checkbox

10. Load schools for School_ID dropdown from:
/api/schools

11. Do not expose Password_Hash anywhere in HTML or API JSON.

12. Add tests:
- Admin can access user management page
- Non-admin cannot access user management page
- GET /api/users hides Password_Hash
- Admin can create user
- Duplicate email rejected
- Invalid role rejected
- School_User requires School_ID
- Admin can deactivate user
- Admin can reset password
- user management actions write audit logs

13. Preserve existing login, forms, stock, requisition, and dashboard functionality.

14. Ensure python -m pytest passes.
