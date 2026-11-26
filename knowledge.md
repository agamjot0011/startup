# WZDM LiveRecord — Complete Development Handbook

## Overview

WZDM LiveRecord is a practice-wide care-coordination platform for orthodontic teams. It combines:

- **FastAPI + Supabase PostgreSQL** backend with role-based patient inboxes
- **React PWA** frontend with per-role dashboards
- **Care loops** (trigger-based clinical workflows)
- **Card system** (role inboxes with acknowledged, started, and completed states)
- **Import/PMS pipeline** with idempotency and outbox-dispatch for compliance
- **Audit & privacy** with proxy relationships, consents, and audit entries

## Project Structure

```
wzdm/
├── backend/                    # FastAPI + Supabase app
│   ├── app/
│   │   ├── api/routes/         # All feature routes
│   │   ├── models/             # SQLAlchemy models
│   │   ├── services/           # Business logic
│   │   ├── schemas/            # Pydantic schemas
│   │   ├── db/                 # Database sessions
│   │   ├── core/               # App config
│   │   └── main.py             # FastAPI app entry point
│   ├── migrations/             # Alembic migrations
│   ├── tests/                  # Test suite
│   ├── requirements.txt
│   └── .env                    # Supabase credentials
├── frontend/                   # React PWA
│   ├── src/
│   │   ├── pages/              # All page components
│   │   ├── App.jsx             # Routing
│   │   └── api.js              # API client
│   └── package.json
├── server.py                   # Backend entry point
├── config.py                   # Project-level config
├── database.py                 # DB helpers
├── auth_utils.py               # Auth helpers
├── schemas.py                  # Shared schemas
├── middleware.py               # Custom middleware
├── routes/auth.py              # Auth routes
└── database_schema.sql         # Supabase schema
```

## Running the Project

1. Copy Supabase credentials into `backend/.env`
2. Run the backend: `uvicorn server:app --reload` (or `python server.py`)
3. Run the frontend: `cd frontend && npm install && npm run dev`
4. Run tests: `pytest backend/tests`

## Key API Endpoints

| Prefix | Feature | Endpoints |
|--------|---------|-----------|
| `/health` | Health checks | `/health/live`, `/health/ready` |
| `/v1/sessions` | Session management | `/me`, `/practice-context`, `/current` |
| `/v1/family` | Family invitations | `/invitations`, `/recovery` |
| `/v1/patients` | Patient inboxes | `/`, `/:id/family-home`, `/:id/timeline`, `/:id/tasks/today` |
| `/v1/cards` | Role inboxes | `/`, `/:id/acknowledgements`, `/:id/starts` |
| `/v1/operations` | Huddle & alerts | `/huddle`, `/loop-report`, `/alert-budget` |
| `/v1/rule-sets` | Clinical loops | `/`, `/:id/versions` |
| `/v1/content-items` | Patient education | `/`, `/:id/versions` |
| `/v1/proxy-relationships` | Proxy access | `/`, `/:id` |
| `/v1/consents` | Consent management | `/`, `/:id` |
| `/v1/imports` | PMS import | `/pms`, `/:id` |
| `/v1/audit` | Audit log | `/` |
| `/v1/exports` | Export & packaging | `/` |

## Compliance & Security

- Every patient has a privacy scope (`PATIENT_PRIVATE`, `PATIENT_PARENT_SHARED`)
- Role-based access to patient data
- All writes go through outbox messages
- Audits are immutable, append-only
- Proxy relationships enforce delegated authority
- Consents are versioned and revocable
