# WZDM LiveRecord — Full Technical Documentation

## 1. Prerequisites

- **Python 3.10+** with a virtual environment
- **Node.js 18+** for the frontend
- **Supabase project** with PostgreSQL database
- **Git** for version control

## 2. Backend Setup

### 2.1 Install dependencies

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2.2 Configure Supabase

1. Go to your Supabase dashboard → **Settings → API**
2. Copy `Project URL` and `anon public` key into `backend/.env`
3. (Optional) Copy `service_role` key for administrative operations

### 2.3 Database setup

The schema is defined in `database_schema.sql`. Apply it via:

```bash
# Option 1: psql
psql -h <SUPABASE_HOST> -U postgres -d postgres -f database_schema.sql

# Option 2: Supabase dashboard
Run SQL in the SQL Editor with the schema file contents
```

### 2.4 Run the backend

```bash
cd backend
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:4000`.

## 3. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:5173`.

## 4. Testing

```bash
cd backend
pytest tests/
```

The test suite covers:
- Health endpoints
- Session management
- Patient inboxes
- Card lifecycle
- Clinical loops
- Import/PMS pipeline
- Privacy and audit

## 5. Architecture Overview

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   React      │────▶│  FastAPI     │────▶│  Supabase    │
│   Frontend   │     │  Backend     │     │  PostgreSQL  │
└──────────────┘     └──────────────┘     └──────────────┘
                                │
                                ▼
                        ┌──────────────┐
                        │  Supabase    │
                        │  Auth & API  │
                        └──────────────┘
```

## 6. Key Concepts

### 6.1 Care Loops

Care loops are trigger-based clinical workflows. When a care event occurs:

1. The event is recorded in the `care_events` table
2. A rule engine matches the event to a rule set
3. New cards are created for assigned roles
4. Cards are visible in the patient's inbox
5. Role holders acknowledge, start, and record results

### 6.2 Card Lifecycle

- `available` → awaiting assignment
- `acknowledged` → role holder saw the card
- `in_progress` → work started
- `result_recorded` → outcome documented
- `closed` → loop finished
- `cancelled` → manually closed

### 6.3 Import/PMS Pipeline

1. Extract data from PMS system (CSV/SQL)
2. Validate and map into the database schema
3. Store in `import_batches` and `import_rows`
4. Commit import with idempotency check
5. Export to patient records

### 6.4 Audit & Compliance

Every state change is recorded as an audit entry:

- Actor (user who made the change)
- Action (what was changed)
- Resource (patient, card, loop, etc.)
- Timestamp
- Before/after values

This satisfies the 21 CFR Part 11 / GDPR audit requirements.

## 7. Role-Based Access

| Role | Permissions |
|------|-------------|
| Ambassador | Family home, safety notices, basic tasks |
| Assistant | Briefs, loop observation, card review |
| Orthodontist | Clinical loops, full card management |
| Front Desk | Appointments, family registration |
| Practice Manager | Operations, staff management, reporting |

## 8. Deployment

### 7.1 Backend (Supabase)

- Deploy the FastAPI app to Supabase or a VPS
- Point `SUPABASE_URL` to your database
- Enable CORS for your frontend origin

### 7.2 Frontend

- Build: `npm run build`
- Deploy to a static host (Vercel, Netlify, S3)
- Configure `FRONTEND_URL` to match the production domain

## 9. Troubleshooting

### Database connection errors

Check that `SUPABASE_URL` in `.env` is correct and accessible.

### CORS errors

Ensure `FRONTEND_URL` in `.env` matches your frontend URL.

### Missing tables

Apply `database_schema.sql` to your Supabase project.

### Test failures

Ensure the backend is running and the database is reachable.

## 10. Known Limitations (Alpha)

- OIDC is stubbed; use synthetic credentials
- Supabase storage is simulated
- Card/loop engines are read-only
- All data is synthetic

This will be resolved in the next development phase.
