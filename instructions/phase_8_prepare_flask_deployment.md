Phase 8.1 – Prepare Flask Form API for online deployment.

Goal:
Prepare the Flask form API for deployment to Render or another Python web service host.

Requirements:

1. Ensure scripts/form_api.py exposes a Flask app object named:

app

Example:

app = Flask(__name__)

2. Create a root-level wsgi.py file with:

from scripts.form_api import app

3. Add gunicorn to requirements.txt.

4. Update authentication secret handling:
   - FORM_API_SECRET_KEY must come from environment variable.
   - If missing, development fallback is allowed only locally with a warning.

5. Update Google credentials handling for online deployment:
   - Support local credentials file:
     credentials/service_account.json
   - Also support environment variable:
     GOOGLE_CREDENTIALS

6. If GOOGLE_CREDENTIALS exists:
   - Parse it as JSON.
   - Use it for gspread authentication.
   - Do not write secrets to logs.

7. Preserve local development compatibility.

8. Add a health check route:

GET /health

Return:

{
  "status": "ok"
}

9. Ensure these routes still work:
   - /login
   - /logout
   - /api/items
   - /api/schools
   - /api/warehouses
   - /forms/approve_requisition.html
   - /forms/receive_stock.html
   - /forms/issue_stock.html
   - /forms/requisition_form.html

10. Add tests where practical.
