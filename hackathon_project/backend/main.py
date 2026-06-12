import os
import sys

# Add backend directory to Python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from routers import workspace, upload, extract, capability, compliance, proposal
from sqlalchemy import text

# Auto-initialize database tables on start
try:
    Base.metadata.create_all(bind=engine)
    print("Database tables initialized successfully.")
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE compliance_results ADD COLUMN IF NOT EXISTS confidence_score INTEGER;"))
        conn.execute(text("ALTER TABLE uploaded_documents ALTER COLUMN file_type TYPE VARCHAR(255);"))
        conn.commit()
    print("Database migration: columns verified/added.")
except Exception as e:
    print(f"WARNING: Database initialization/migration failed: {e}")
    print("FastAPI will start, but database operations might fail.")

app = FastAPI(
    title="AI-Powered Bid Response Engine API",
    description="Backend API for parsing RFPs, managing workspaces, and validating compliance.",
    version="0.1.0"
)

# CORS configuration to enable frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
