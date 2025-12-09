from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio

from database import connect_db, close_db
from routers import auth, jobs, upload
from worker import run_worker

# Background worker task
worker_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global worker_task
    # Startup
    await connect_db()
    # Start worker in background
    worker_task = asyncio.create_task(run_worker())
    print("Worker started in background")
    yield
    # Shutdown
    if worker_task:
        worker_task.cancel()
    await close_db()


app = FastAPI(
    title="LazyDev API",
    description="Automated Git commit scheduler",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://lazydev-web.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router, tags=["Auth"])
app.include_router(upload.router, tags=["Upload"])
app.include_router(jobs.router, tags=["Jobs"])


@app.get("/health")
async def health_check():
    return {"status": "healthy", "app": "LazyDev"}
