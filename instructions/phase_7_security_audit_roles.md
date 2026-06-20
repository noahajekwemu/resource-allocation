Phase 7 – User Roles, Audit Trail, and Security Hardening

Refactor the system to support basic authentication, role-based access control, and audit logging.

IMPORTANT:
Use CLI-compatible changes.
Preserve all existing working functionality.
Do not break existing dashboard deployment.
Do not edit docs/ directly.

FILES TO UPDATE OR CREATE:

- scripts/form_api.py
- scripts/db_connector.py
- scripts/security_utils.py
- scripts/audit_utils.py
- forms/login.html
- forms/logout.html if needed
- forms/receive_stock.html
- forms/issue_stock.html
- forms/requisition_form.html
- forms/approve_requisition.html
- requirements.txt
- tests/test_security_utils.py
- tests/test_audit_utils.py
- tests/test_role_permissions.py

DATABASE WORKSHEETS:

Add support for Users worksheet:

Columns:
- User_ID
- Full_Name
- Email
- Role
- School_ID
- Password_Hash
- Active
- Created_At

Add support for Audit_Log worksheet:

Columns:
- Audit_ID
- Timestamp
- User_ID
- User_Email
- Role
- Action
- Entity_Type
- Entity_ID
- Before_State
- After_State
- IPAddress
- Status
- Remarks

ROLES:

Support these roles:

- Admin
- Approver
- Store_Officer
- School_User
- Viewer

PERMISSIONS:

Admin:
- Can do everything.

Approver:
- Can view pending requisitions.
- Can approve requisitions.
- Can reject requisitions.
- Cannot receive stock.
- Cannot issue stock.

Store_Officer:
- Can receive stock.
- Can issue stock.
- Can fulfill approved requisitions.
- Cannot approve or reject requisitions.

School_User:
- Can submit requisitions only for their assigned School_ID.
- Cannot approve.
- Cannot receive stock.
- Cannot issue stock.

Viewer:
- Can only view public/read-only endpoints.

AUTHENTICATION:

1. Add login route:

GET /login
POST /login

2. Add logout route:

POST /logout or GET /logout

3. Use Flask session authentication.

4. SECRET_KEY must come from environment variable:

FORM_API_SECRET_KEY

If missing, use a development-only fallback with a warning log.

5. Passwords must not be stored in plain text.

Use werkzeug.security:
- generate_password_hash
- check_password_hash

6. Add helper functions in scripts/security_utils.py:

- hash_password(password: str) -> str
- verify_password(password: str, password_hash: str) -> bool
- get_user_by_email(email: str) -> dict | None
- authenticate_user(email: str, password: str) -> dict | None
- require_login()
- require_role(*roles)
- current_user()
- user_can(action: str, user: dict) -> bool

7. In development, provide a CLI helper or documented function to create initial users with hashed passwords.

ROLE PROTECTION:

Protect these endpoints:

submit_requisition:
- Admin
- School_User

approve_requisition:
- Admin
- Approver

reject_requisition:
- Admin
- Approver

submit_receive_stock:
- Admin
- Store_Officer

submit_issue_stock:
- Admin
- Store_Officer

open_requisitions:
- Admin
- Store_Officer
- Approver

pending_requisitions:
- Admin
- Approver

AUDIT LOGGING:

Create scripts/audit_utils.py.

Add function:

write_audit_log(
    action: str,
    entity_type: str,
    entity_id: str,
    before_state: dict | None,
    after_state: dict | None,
    status: str,
    remarks: str = ""
)

Every write action must create an Audit_Log row:

- login success
- failed login
- logout
- submit requisition
- approve requisition
- reject requisition
- receive stock
- issue stock
- fulfillment update

Audit log must include:
- current user
- timestamp
- role
- action
- entity type
- entity id
- before state JSON
- after state JSON
- IP address if available
- status
- remarks

SECURITY HARDENING:

1. Validate all incoming JSON payloads.

2. Reject missing required fields.

3. Reject invalid roles.

4. Reject inactive users.

5. Prevent School_User from submitting requisitions for another school.

6. Prevent unauthenticated write requests.

7. Return consistent JSON errors:

{
  "success": false,
  "error": "message"
}

8. Do not expose Password_Hash through API responses.

9. Add basic CSRF protection for form POSTs if practical.

10. Add security-related logging.

FORMS:

Update these forms to handle login/session errors gracefully:

- receive_stock.html
- issue_stock.html
- requisition_form.html
- approve_requisition.html

If API returns 401:
- Show "Please log in."

If API returns 403:
- Show "You do not have permission to perform this action."

Create forms/login.html with:
- Email
- Password
- Submit button
- Clear error messages

TESTS:

Create tests for:

1. Password hashing and verification.

2. Invalid password rejection.

3. Inactive user rejection.

4. Role permission checks.

5. School_User cannot submit for another school.

6. Approver cannot issue stock.

7. Store_Officer cannot approve requisitions.

8. Audit log payload formatting.

Do not require real Google Sheets writes for unit tests.
Use mocks where possible.

COMPATIBILITY:

Preserve compatibility with:

- Items
- Schools
- Warehouses
- Transactions
- Transaction_Details
- Requisitions
- Requisition_Details
- Audit_Log
- Users
- calculate_metrics.py
- dashboard deployment workflow

OUTPUT:

Provide complete updated file contents.