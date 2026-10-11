# ERP-based Product Duplicate Detection System - Backend

Backend API and database service for the ERP-based Product Duplicate Detection System, built with **FastAPI**, **SQLAlchemy**, and **Supabase PostgreSQL**.

---

## Current Status: Stage 2 Completed

* **Stage 1 (Completed):** Base architecture, FastAPI scaffolding, CORS, and health check.
* **Stage 2 (Completed):** Supabase PostgreSQL connectivity architecture (`app/database.py`), connection pooling, Alembic migration configuration (`alembic/`), database health check endpoint (`/health/db`), and connection test script (`scripts/test_db_connection.py`).

> **Note:** Product models, duplicate-detection tables, and Alembic migrations will be created in **Stage 3**.

---

## Project Structure

```text
Backend/
├── alembic/                 # Alembic database migrations
│   ├── versions/            # Migration scripts (populated in Stage 3+)
│   ├── env.py               # Migration environment wired to app.config and app.database
│   ├── README
│   └── script.py.mako
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app instance, CORS, error handling, /health, /health/db
│   ├── config.py            # Pydantic Settings & dynamic Supabase connection string parser
│   ├── database.py          # SQLAlchemy engine (pooled), SessionLocal, Base, get_db()
│   ├── models/              # SQLAlchemy ORM models (Stage 3)
│   │   └── __init__.py
│   ├── schemas/             # Pydantic schemas (Stage 4)
│   │   └── __init__.py
│   ├── routers/             # API route controllers (Stage 4+)
│   │   └── __init__.py
│   ├── services/            # Business logic services (Stage 4+)
│   │   └── __init__.py
│   ├── repositories/        # Database access layer (Stage 4+)
│   │   └── __init__.py
│   ├── ml/                  # ML interface and duplicate detection model (Stage 6)
│   │   └── __init__.py
│   └── utils/               # File parsers and utilities (Stage 5)
│       └── __init__.py
├── scripts/
│   ├── __init__.py
│   └── test_db_connection.py # Standalone Supabase connectivity verification script
├── tests/                   # Automated unit & integration tests
│   ├── __init__.py
│   └── test_main.py
├── uploads/                 # Temporary storage for bulk CSV/Excel files (Stage 5)
├── .env                     # Local environment variables (git-ignored)
├── .env.example             # Template for environment variables (includes Supabase formats)
├── .gitignore               # Git ignore rules
├── alembic.ini              # Alembic configuration
├── pytest.ini               # Pytest configuration
├── requirements.txt         # Project dependencies
└── README.md                # Documentation and setup guide
```

---

## Supabase PostgreSQL Configuration

### 1. Create a Supabase Project
1. Log in to [Supabase](https://supabase.com) and create or open your project.
2. Go to **Project Settings** (gear icon in sidebar) -> **Database**.
3. Under **Connection String**, select **URI**.

### 2. Connection String Options
* **Option A: Connection Pooler (Recommended for Cloud/FastAPI - Port 6543)**
  ```text
  postgresql+psycopg://postgres.[PROJECT_REF]:[YOUR_PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres?sslmode=require
  ```
* **Option B: Direct Connection (Port 5432)**
  ```text
  postgresql+psycopg://postgres:[YOUR_PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres?sslmode=require
  ```

> **Important:** If your database password contains special characters (like `@`, `!`, `#`, `/`), they must be URL-encoded (e.g., replace `@` with `%40`, `!` with `%21`).

### 3. Add to `.env`
Update `DATABASE_URL` in your `.env` file:
```env
DATABASE_URL=postgresql+psycopg://postgres.yourprojectref:yourpassword@aws-0-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require
```

---

## Verifying Database Connection

### Run the Standalone Connection Script
```powershell
.\.venv\Scripts\Activate.ps1
python scripts/test_db_connection.py
```
* On success, this executes `SELECT 1;` and prints the connected PostgreSQL version.

### Verify via Alembic
Once your Supabase credentials are in `.env`:
```powershell
alembic current
```

---

## Running the Backend

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Endpoints
* **Root API:** [http://localhost:8000/](http://localhost:8000/)
* **App Health:** [http://localhost:8000/health](http://localhost:8000/health)
* **Database Health:** [http://localhost:8000/health/db](http://localhost:8000/health/db)
* **Interactive Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
