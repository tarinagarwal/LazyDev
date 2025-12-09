from fastapi import APIRouter, Depends, HTTPException
from typing import List
from datetime import datetime

from routers.auth import verify_token
from models import JobResponse, JobDetailResponse, JobStatus, CommitStatus, TokenData
from database import get_db

router = APIRouter()


@router.get("/jobs", response_model=List[JobResponse])
async def list_jobs(token: TokenData = Depends(verify_token)):
    """List all jobs"""
    db = get_db()
    cursor = db.jobs.find().sort("created_at", -1)
    jobs = await cursor.to_list(length=100)
    
    return [
        JobResponse(
            id=str(job["id"]),
            repo=job["repo"],
            status=job["status"],
            total_commits=job["total_commits"],
            completed_commits=job["completed_commits"],
            created_at=job["created_at"],
            started_at=job.get("started_at"),
            finished_at=job.get("finished_at"),
            error=job.get("error")
        )
        for job in jobs
    ]


@router.get("/jobs/{job_id}", response_model=JobDetailResponse)
async def get_job(job_id: str, token: TokenData = Depends(verify_token)):
    """Get job details"""
    db = get_db()
    job = await db.jobs.find_one({"id": job_id})
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobDetailResponse(
        id=str(job["id"]),
        repo=job["repo"],
        status=job["status"],
        total_commits=job["total_commits"],
        completed_commits=job["completed_commits"],
        created_at=job["created_at"],
        started_at=job.get("started_at"),
        finished_at=job.get("finished_at"),
        error=job.get("error"),
        commits=job["commits"]
    )


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str, token: TokenData = Depends(verify_token)):
    """Cancel a pending or in-progress job"""
    db = get_db()
    job = await db.jobs.find_one({"id": job_id})
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job["status"] in [JobStatus.COMPLETED, JobStatus.CANCELLED, JobStatus.FAILED]:
        raise HTTPException(status_code=400, detail=f"Cannot cancel job with status: {job['status']}")
    
    # Update job status
    await db.jobs.update_one(
        {"id": job_id},
        {
            "$set": {
                "status": JobStatus.CANCELLED,
                "finished_at": datetime.utcnow()
            }
        }
    )
    
    # Mark pending commits as cancelled
    commits = job["commits"]
    for i, commit in enumerate(commits):
        if commit["status"] == CommitStatus.PENDING:
            commits[i]["status"] = CommitStatus.SKIPPED
    
    await db.jobs.update_one(
        {"id": job_id},
        {"$set": {"commits": commits}}
    )
    
    return {"message": "Job cancelled successfully"}
