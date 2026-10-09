# AI-Powered Task Management System

A REST API for authenticated task management, built with **FastAPI**, **PostgreSQL**, **SQLAlchemy 2.0**, **Alembic**, **JWT** authentication and the **Google Gemini** API. Users manage their own tasks. Administrators can see and manage every task. Two AI features generate task descriptions and summaries.

## Key features

- User registration and login. Passwords are hashed with Argon2id. Login returns a JWT.
- Role-based access control with two roles, `user` and `admin`, enforced in the backend.
- Task CRUD for owners and administrators, plus an admin-only status endpoint.
- Four task statuses: `Pending`, `In Progress`, `Testing`, `Completed`.
- AI feature A: `POST /api/tasks/generate-description`. Generates a description from a title.
- AI feature B: `POST /api/tasks/{id}/summarize`. Summarises a task's title and description.
- Consistent JSON error responses, with no passwords, tokens, SQL, or provider details exposed.
- Alembic migrations, an idempotent development seeder, pytest tests with Gemini mocked, and a Postman collection.

## Technology stack

| Area | Choice |
|---|---|
| Language | Python 3.11+ (tested on 3.12) |
| Web framework | FastAPI 0.115 with Uvicorn |
| Database | PostgreSQL 14+ (tested on 16) via SQLAlchemy 2.0 and psycopg 3 |
| Migrations | Alembic |
| Validation | Pydantic 2 and pydantic-settings |
| Authentication | PyJWT (HS256) and argon2-cffi (Argon2id password hashing) |
| AI provider | Google Gemini `generateContent` REST API, called through httpx |
| Tests | pytest, FastAPI TestClient, httpx MockTransport |

## Folder structure

```
ai-task-manager/
├── app/
│   ├── main.py              # FastAPI app factory and entry point
│   ├── api/                 # HTTP routes: auth.py, tasks.py (includes the AI endpoints)
│   ├── auth/                # security.py (hashing, JWT), dependencies.py (current user, admin)
│   ├── ai/                  # AI feature code: gemini_client.py, service.py, prompts.py, schemas.py
│   ├── core/                # config.py (settings), exceptions.py, error_handlers.py
│   ├── database/            # session.py (engine, get_db), seed.py (development seeder)
│   ├── models/              # SQLAlchemy models: User, Task, enums
│   ├── schemas/             # Pydantic request and response models
│   └── services/            # Business logic: user_service, task_service, permissions
├── migrations/              # Alembic environment and versions/0001_initial_schema.py
├── tests/                   # pytest suite (auth, security, tasks, permissions, AI, errors)
├── postman/                 # AI-Task-Management.postman_collection.json
├── alembic.ini
├── pyproject.toml           # pytest and ruff settings
├── requirements.txt         # pinned dependencies
└── .env.example             # configuration template (copy to .env)
```

## Prerequisites

- **Python 3.11 or newer.** Download it from python.org and tick "Add python.exe to PATH".
- **PostgreSQL 14 or newer.** Install it with the EDB installer from postgresql.org. Keep the default port 5432, and note the password you set for the `postgres` user.
- **Git** (optional), and **Postman** (optional, for the API collection).

## Setup on Windows 11 (PowerShell)

All commands run from the project root folder.

**1. Create and activate a virtual environment**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks the activation script, run this once and try again:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

**2. Install the dependencies**

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**3. Create the databases**

Replace `YOUR_PASSWORD` with the password you chose during the PostgreSQL installation. If `psql` is not on your PATH, use its full path, usually `"C:\Program Files\PostgreSQL\16\bin\psql.exe"`.

```powershell
psql -U postgres -c "CREATE DATABASE task_manager;"
psql -U postgres -c "CREATE DATABASE task_manager_test;"
```

`task_manager_test` is used only by the automated tests.

**4. Configure the environment**

```powershell
Copy-Item .env.example .env
notepad .env
```

Set `DATABASE_URL` to match your PostgreSQL password, and replace the JWT secret with a random value of at least 32 characters:

```
DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/task_manager
JWT_SECRET_KEY=<paste output of the command below>
```

To generate a secret, run `python -c "import secrets; print(secrets.token_urlsafe(48))"`. If your password contains characters such as `@`, `:` or `/`, URL-encode them in `DATABASE_URL`.

**5. Apply the migrations and seed development data**

```powershell
alembic upgrade head
python -m app.database.seed
```

The seeder is safe to run more than once. It skips accounts and tasks that already exist.

**6. Start the server**

```powershell
uvicorn app.main:app --reload
```

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc
- Health check: http://127.0.0.1:8000/health

## Environment variables

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `DATABASE_URL` | yes | none | SQLAlchemy URL, for example `postgresql+psycopg://user:pass@localhost:5432/task_manager` |
| `JWT_SECRET_KEY` | yes | none | Signing key for JWTs. At least 32 characters. The app refuses to start with the `.env.example` placeholder. |
| `JWT_ALGORITHM` | no | `HS256` | JWT signing algorithm |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | no | `60` | Token lifetime |
| `GEMINI_API_KEY` | for AI | empty | Google Gemini API key. Leave empty to run without AI. |
| `GEMINI_MODEL` | no | `gemini-2.5-flash` | Gemini model name. Change it if Google retires this model. |
| `GEMINI_BASE_URL` | no | Google v1beta endpoint | Override only for proxies or tests |
| `GEMINI_TIMEOUT_SECONDS` | no | `20` | Timeout for each AI request |

Real values go in `.env`, which is git-ignored. `.env.example` lists every variable with safe placeholders.

## Configuring the Gemini API

1. Create an API key in Google AI Studio (https://aistudio.google.com/app/apikey).
2. Add it to `.env`: `GEMINI_API_KEY=your-key-here`.
3. Restart Uvicorn.

Without a key the application still starts. The two AI endpoints then return `503` with `"code": "ai_not_configured"`. The rest of the API works normally. The key is sent only in the `x-goog-api-key` request header and is never logged or returned.

AI errors use these codes:

| Situation | HTTP status | `error.code` |
|---|---|---|
| No API key configured | 503 | `ai_not_configured` |
| Provider did not answer in time | 504 | `ai_timeout` |
| Network error, provider HTTP error, or prompt blocked | 502 | `ai_provider_error` (blocked prompts return `ai_invalid_response`) |
| Output is not the expected JSON, or fails validation | 502 | `ai_invalid_response` |

The model is asked for JSON (`responseMimeType: application/json`). The response is then parsed and validated with Pydantic, including length limits. Invalid output is rejected, not returned to the client.

## Running the database migrations

```powershell
alembic upgrade head        # apply all migrations
alembic downgrade base      # roll everything back (development only)
alembic current             # show the current revision
alembic check               # confirm the models match the migrations (should print "No new upgrade operations")
```

The schema is defined in `migrations/versions/0001_initial_schema.py`. There is no separate SQL file.

## Seeded test credentials

Created by `python -m app.database.seed`. **Development only.** Never use these in a real deployment.

| Role | Email | Password |
|---|---|---|
| Administrator | `admin@example.com` | `Admin@12345` |
| Regular user | `user@example.com` | `User@12345` |
| Regular user | `user2@example.com` | `User2@12345` |

The seed data also includes sample tasks. The regular user `user@example.com` has three tasks, which is useful for checking that a user sees only their own tasks.

## Example authentication workflow

**PowerShell**

```powershell
$login = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/auth/login `
  -ContentType "application/json" `
  -Body '{"email":"user@example.com","password":"User@12345"}'

$headers = @{ Authorization = "Bearer $($login.access_token)" }
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/tasks -Headers $headers
```

**curl** (Git Bash or WSL)

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"User@12345"}' | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
curl -s http://127.0.0.1:8000/api/tasks -H "Authorization: Bearer $TOKEN"
```

In Swagger UI, log in through `POST /api/auth/login`, copy `access_token`, and paste it into the **Authorize** dialog.

## API endpoints

All endpoints except registration, login and `/health` require `Authorization: Bearer <token>`.

| Method | Path | Who | Description |
|---|---|---|---|
| GET | `/health` | anyone | Liveness check |
| POST | `/api/auth/register` | anyone | Create a regular user (201) |
| POST | `/api/auth/login` | anyone | Log in and receive a JWT |
| GET | `/api/auth/me` | any user | Current user profile |
| POST | `/api/tasks` | any user | Create a task. It starts as `Pending` and belongs to the caller. |
| GET | `/api/tasks` | user: own, admin: all | List tasks. Query: `status`, `skip`, `limit` (max 100). |
| GET | `/api/tasks/{id}` | owner or admin | View a task |
| PATCH | `/api/tasks/{id}` | owner or admin | Edit `title` and/or `description`. Sending `status` returns 422. |
| PATCH | `/api/tasks/{id}/status` | admin only | Change the status. Non-admins receive 403. |
| POST | `/api/tasks/generate-description` | any user | **AI (Option A).** Body: `{"title": "..."}`. Returns a generated description. Does not save anything. |
| POST | `/api/tasks/{id}/summarize` | owner or admin | **AI (Option B).** Returns a summary of the task's title and description. Does not save anything. |

Example request body for creating a task:

```json
{ "title": "Prepare sprint review", "description": "Slides and metrics." }
```

## Access control rules

| Action | Regular user | Admin |
|---|---|---|
| Register, log in, view own profile | yes | yes |
| Create tasks | yes (own) | yes (own) |
| List and view tasks | own tasks only | all tasks |
| Edit title or description | own tasks only | all tasks |
| Change status | no (403) | yes |
| Use AI endpoints on own tasks | yes | yes |
| Use AI summary on another user's task | no (403) | yes |

Access is checked in the backend, in `app/services/permissions.py` and in the status route's dependency. The tests in `tests/test_permissions.py` cover these rules.

## Error format

Every error uses the same shape:

```json
{ "error": { "code": "forbidden", "message": "You do not have access to this task." } }
```

Validation errors (422) also include a `details` list with the field name and message. Submitted values are never echoed back.

| Status | Code | Typical cause |
|---|---|---|
| 400 | `bad_request` | Malformed request |
| 401 | `unauthorized` | Missing, invalid or expired token; wrong login credentials |
| 403 | `forbidden` | Authenticated but not allowed |
| 404 | `not_found` | Task does not exist |
| 409 | `conflict` | Email already registered |
| 422 | `validation_error` | Invalid or unexpected input |
| 500 | `database_error` / `internal_error` | Server-side failure (details are logged, not returned) |
| 502 / 503 / 504 | `ai_*` | AI provider failure (see the Gemini section) |

## Running the automated tests

The tests use a separate database, `task_manager_test`, which is emptied between tests. The database name must contain `test`, or the tests refuse to run. Gemini is never called during testing.

```powershell
$env:TEST_DATABASE_URL = "postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/task_manager_test"
pytest
```

To run the linter:

```powershell
ruff check app tests migrations
```

## Postman collection

1. Start the server.
2. In Postman choose **Import** and select `postman/AI-Task-Management.postman_collection.json`.
3. Check the collection variables. `baseUrl` is `http://127.0.0.1:8000`, and the seeded credentials are filled in.
4. Open the collection and click **Run**. Run it from top to bottom, because later folders depend on task IDs created earlier.

The login and create requests save the JWTs and task IDs into collection variables automatically. The AI requests accept either a successful result or a documented AI error, so the collection passes with or without a Gemini key.

To create an administrator, use the seeded admin account, or promote a user yourself with `UPDATE users SET role = 'admin' WHERE email = 'name@example.com';` in psql. Registration always creates regular users.

## Assumptions and implementation decisions

- **403 vs 404.** Requesting another user's task returns 403. A task that does not exist returns 404. Because task IDs are sequential integers, this reveals whether an ID exists. Returning 404 for both would hide that, at the cost of less precise error messages. I chose 403 to keep the access rules explicit for the assessment.
- **New tasks start as `Pending`.** Status cannot be supplied on create, so ordinary users cannot create completed tasks.
- **Status is changed only through `PATCH /api/tasks/{id}/status`, which is admin-only.** General edits reject a `status` field with 422, so the rule cannot be bypassed by adding an extra field.
- **Admin-created tasks belong to the admin.** Admins create tasks for themselves. The PDF does not define task assignment, so there is none.
- **Registration cannot set a role.** Requests containing `role` return 422.
- **JWTs** are signed with HS256 and expire after 60 minutes by default. The role claim is informational. On every request the user is reloaded from the database, so deleted accounts and role changes take effect immediately. Logout and token revocation are not implemented, and tokens remain valid until they expire.
- **Passwords** must be 8 to 128 characters. They are hashed with Argon2id. Login failures return the same message whether the email or the password is wrong, and the code takes similar time in both cases.
- **Login is not rate-limited.** Brute-force protection would be a sensible next step for production.
- **AI results are not saved.** Both AI endpoints return generated text, and the client decides whether to store it. This keeps AI output separate from the task data.
- **Gemini model names change over time.** The default is set by `GEMINI_MODEL`. If the default stops working, change it in `.env`.
- **Migrations.** There is one initial migration. The test suite builds the schema directly from the models for speed. `alembic check` confirms that the models and migration match.
- **Pagination.** `GET /api/tasks` returns `items`, `total`, `skip` and `limit`. The default page size is 20 and the maximum is 100.

## Deliberately out of scope

Refresh tokens, token revocation, login rate limiting, email verification, a frontend, and task deletion were not part of the assignment and are not implemented.
