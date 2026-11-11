# InfraSync React frontend

This is a new React/Vite frontend shell for the existing Flask application. It does not modify or replace Flask routes, Supabase code, CatBoost, risk calculations, or task services.

## Install

From the project root (the folder containing `app.py`):

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite address shown in the terminal, normally `http://127.0.0.1:5173`.

Keep Flask running separately in another PowerShell window:

```powershell
# From the project root
python app.py
```

## Build

```powershell
cd frontend
npm run build
```

The production build is written to `frontend/dist`.

## Important integration note

The role selector opens the existing Flask dashboard and project-details page inside the React workspace. It uses the existing `/dashboard` and `/project/<project_id>?view=<role>` routes. This is deliberately conservative so existing backend behavior remains intact.

Before adding direct React forms for task creation, team editing, client data, or risk displays, verify the exact request/response contracts of the existing APIs. Do not change backend logic just to match the frontend.
