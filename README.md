# Bahamas AI Trading — Backend (FastAPI + PostgreSQL)

REST API serving both the public website and the admin console.

## Run locally
```bash
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env    # fill DATABASE_URL, SECRET_KEY, FERNET_KEY (commands inside)
python -m scripts.create_admin admin              # interactive password prompt
python -m scripts.seed_demo                       # OPTIONAL demo data (dev/staging only)
uvicorn app.main:app --reload                     # http://localhost:8000/api/docs
```

## Endpoints
| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | /api/v1/onboarding | — | Client application → reference code |
| POST | /api/v1/kyc/upload | — | KYC file (magic-byte validated, encrypted at rest) |
| POST | /api/v1/contact | — | Support message |
| POST | /api/v1/auth/login | — | Admin JWT |
| GET | /api/v1/admin/stats | JWT | Dashboard metrics |
| GET | /api/v1/admin/submissions?q=&status=&limit=&offset= | JWT | Search/filter/paginate |
| PATCH | /api/v1/admin/submissions/{id}/status | JWT | pending/reviewed/approved/rejected |
| GET | /api/v1/admin/kyc/{doc_id} | JWT | Decrypt + stream document (audited) |
| GET | /api/v1/admin/contact-messages | JWT | Support inbox |

## Deploying standalone
Any Docker host works: `docker build -t bat-api . && docker run --env-file .env -p 8000:8000 -v kyc:/data/uploads bat-api`.
Set `ENVIRONMENT=production` (disables /api/docs) and put real origins in `CORS_ORIGINS`
(both the website and the admin console domains). Terminate TLS in front (Caddy/nginx/load balancer).

## Security notes
KYC files: validated by magic bytes, ≤10 MB, random names, Fernet-encrypted, private volume,
admin-only streaming with audit logging. Never mount `/data/uploads` into a web-served path.
`seed_demo` creates `admin / AdminPass123!` — never run it against production.
