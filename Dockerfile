FROM python:3.12-slim

WORKDIR /srv

# ── Dependencies ──────────────────────────────────────────────────────────────
# Copied first so this layer is cached and only rebuilds when requirements change.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Application source ────────────────────────────────────────────────────────
COPY . .

# ── Runtime user + upload directories ─────────────────────────────────────────
# /data/uploads  — production volume mount (set UPLOAD_DIR=/data/uploads in env)
# /srv/uploads   — fallback for dev/staging without a mounted volume
# Both owned by appuser so the process can write to either path.
RUN useradd -m appuser \
 && mkdir -p /data/uploads /srv/uploads \
 && chown -R appuser:appuser /data/uploads /srv/uploads /srv

USER appuser

EXPOSE 8000

# ── Health check ──────────────────────────────────────────────────────────────
# Uses Python's stdlib urllib — no curl/wget needed in the slim image.
# Calls /api/health which runs SELECT 1 against the database.
# The endpoint returns HTTP 200 when healthy, HTTP 503 when the DB is down.
# urllib raises HTTPError on 4xx/5xx → Python exits 1 → Docker marks unhealthy.
#
# Timing:
#   --start-period=15s  give uvicorn + DB time to initialise before first check
#   --interval=30s      check every 30 seconds
#   --timeout=10s       kill the check if it hangs longer than 10 s
#   --retries=3         mark unhealthy only after 3 consecutive failures
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD python -c \
    "import urllib.request, sys; \
     r = urllib.request.urlopen('http://localhost:8000/api/health', timeout=8); \
     sys.exit(0 if r.status == 200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]