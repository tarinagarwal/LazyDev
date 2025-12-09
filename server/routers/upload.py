from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from datetime import datetime
import uuid
import json

from routers.auth import verify_token
from models import CommitPlanRequest, CommitRecord, Job, JobStatus, CommitStatus, TokenData
from database import get_db
from services.storage import upload_to_r2
from services.github import repo_exists, create_repo
from worker import queue_job

router = APIRouter()


@router.post("/upload")
async def upload_job(
    zip_file: UploadFile = File(...),
    commit_plan: str = Form(...),
    token: TokenData = Depends(verify_token)
):
    """Upload zip file and commit plan to create a new job"""
    
    # Parse commit plan
    try:
        plan_data = json.loads(commit_plan)
        plan = CommitPlanRequest(**plan_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid commit plan: {str(e)}")
    
    # Validate zip file
    if not zip_file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="File must be a .zip archive")
    
    # Check/create GitHub repo
    if not await repo_exists(plan.repo):
        created = await create_repo(plan.repo)
        if not created:
            raise HTTPException(status_code=400, detail=f"Failed to create repository: {plan.repo}")
    
    # Generate unique key for R2
    job_id = str(uuid.uuid4())
    zip_key = f"jobs/{job_id}/source.zip"
    
    # Upload to R2
    content = await zip_file.read()
    await upload_to_r2(content, zip_key)
    
    # Create commit records
    commits = [
        CommitRecord(
            files=c.files,
            message=c.message,
            delay_mins=c.delay_mins,
            status=CommitStatus.PENDING
        )
        for c in plan.commits
    ]
    
    # Create job document
    job = Job(
        id=job_id,
        repo=plan.repo,
        zip_key=zip_key,
        commits=commits,
        status=JobStatus.PENDING,
        total_commits=len(commits),
        created_at=datetime.utcnow()
    )
    
    # Save to MongoDB
    db = get_db()
    await db.jobs.insert_one(job.model_dump(by_alias=True))
    
    # Queue the job for processing
    await queue_job(job_id)
    
    return {
        "message": "Job created successfully",
        "job_id": job_id,
        "total_commits": len(commits)
    }
