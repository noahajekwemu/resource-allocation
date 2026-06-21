Fix CORS for Phase 9 dashboard API status check.

Problem:
https://resource-allocation-api.onrender.com/health works directly in the browser, but the public dashboard shows API Offline.

Cause:
The dashboard is served from GitHub Pages or localhost:8000 and fetches /health from Render. Browser CORS may block the request.

Requirements:

1. Update scripts/form_api.py.

2. Add flask-cors support.

3. Add flask-cors to requirements.txt if missing.

4. Allow GET requests to /health from these origins:
- https://noahajekwemu.github.io
- http://127.0.0.1:8000
- http://localhost:8000

5. Do not open protected write endpoints broadly.

6. Do not weaken login, sessions, role checks, or audit logging.

7. Preserve:
- /login
- /logout
- /health
- /forms/<filename>
- /api/items
- /api/schools
- /api/warehouses

8. Ensure python -m pytest passes.
