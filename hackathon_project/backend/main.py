import os
import sys

# Add backend directory to Python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from database import engine, Base
from routers import workspace, upload, extract, capability, compliance, proposal
from sqlalchemy import text

# ── Configuration ────────────────────────────────────────────────────────────
# Restrict origins: add your production domain here when deploying.
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Max upload size accepted by FastAPI (10 MB)
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB

# Auto-initialize database tables on start
try:
    Base.metadata.create_all(bind=engine)
    print("Database tables initialized successfully.")
except Exception as e:
    print(f"WARNING: Database initialization failed: {e}")
    print("FastAPI will start, but database operations might fail.")

# Run migrations individually so one failure doesn't block another
with engine.connect() as conn:
    for migration_sql in [
        "ALTER TABLE compliance_results ADD COLUMN IF NOT EXISTS confidence_score INTEGER;",
        "ALTER TABLE uploaded_documents ALTER COLUMN file_type TYPE VARCHAR(255);",
    ]:
        try:
            conn.execute(text(migration_sql))
            conn.commit()
        except Exception as _e:
            print(f"Migration skipped (may already be applied): {_e}")
print("Database migration: columns verified/added.")

app = FastAPI(
    title="AI-Powered Bid Response Engine API",
    description="Backend API for parsing RFPs, managing workspaces, and validating compliance.",
    version="0.1.0",
    # Disable interactive docs in production — set to None to hide Swagger/ReDoc
    # docs_url=None,
    # redoc_url=None,
)

# CORS — only allow known frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
)


@app.middleware("http")
async def limit_upload_size(request: Request, call_next):
    """Reject requests whose body exceeds MAX_UPLOAD_BYTES to prevent DoS."""
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_UPLOAD_BYTES:
        return JSONResponse(
            status_code=413,
            content={"detail": f"Request body too large. Maximum allowed size is {MAX_UPLOAD_BYTES // (1024*1024)} MB."},
        )
    return await call_next(request)

# Include routers
app.include_router(workspace.router)
app.include_router(upload.router)
app.include_router(extract.router)
app.include_router(capability.router)
app.include_router(compliance.router)
app.include_router(proposal.router)


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "Bid Response Engine API"}
