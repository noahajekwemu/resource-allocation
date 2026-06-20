from flask import send_from_directory, redirect, url_for, request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
FORMS_DIR = BASE_DIR / "forms"

FORM_PAGE_ROLES = {
    "approve_requisition.html": {"Admin", "Approver"},
    "receive_stock.html": {"Admin", "Store_Officer"},
    "issue_stock.html": {"Admin", "Store_Officer"},
    "requisition_form.html": {"Admin", "School_User"},
}

@app.route("/forms/<path:filename>")
def serve_form(filename):
    if filename == "login.html":
        return redirect(url_for("login"))

    user = current_user()
    if not user:
        return redirect(url_for("login", next=f"/forms/{filename}"))

    allowed_roles = FORM_PAGE_ROLES.get(filename)
    if allowed_roles is None:
        return {"success": False, "error": "Form not found."}, 404

    if user.get("Role") not in allowed_roles:
        return {"success": False, "error": "You do not have permission to access this page."}, 403

    return send_from_directory(FORMS_DIR, filename)