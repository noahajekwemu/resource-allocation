Fix Audit_Log worksheet formatting.

Problem:
Audit_Log is not populating properly because the worksheet may not have headers.
Rows are being appended into incorrect columns when headers are missing.

Requirements:

1. Update scripts/audit_utils.py.

2. Define a constant:

AUDIT_LOG_HEADERS = [
  "Audit_ID",
  "Timestamp",
  "User_ID",
  "User_Email",
  "Role",
  "Action",
  "Entity_Type",
  "Entity_ID",
  "Before_State",
  "After_State",
  "IPAddress",
  "Status",
  "Remarks"
]

3. Before writing any audit log row:
   - Read the first row of Audit_Log.
   - If headers are missing or incorrect, write AUDIT_LOG_HEADERS into row 1.
   - Append audit rows only after the header row.

4. Audit rows must always be appended in this exact column order:
   Audit_ID
   Timestamp
   User_ID
   User_Email
   Role
   Action
   Entity_Type
   Entity_ID
   Before_State
   After_State
   IPAddress
   Status
   Remarks

5. Before_State and After_State must be JSON strings.

6. Ensure failed login, successful login, logout, receive stock, issue stock, submit requisition, approve requisition, reject requisition, and fulfillment update all write properly formatted audit rows.

7. Add tests for:
   - audit header creation
   - audit row column ordering
   - before_state and after_state JSON serialization
   - failed login audit payload
   - successful login audit payload

8. Do not break existing role-based access control.
