import redis
import asyncio
import os
import shutil
import tempfile
import zipfile
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient

from config import get_settings
from models import JobStatus, CommitStatus
from services.storage import download_from_r2, delete_from_r2
from services.github import setup_git_repo, commit_files, push_to_remote
from services.email import send_commit_notification, send_job_complete_notification

settings = get_settings()

# Redis connection (lazy init)
redis_client = None

def get_redis():
    global redis_client
    if redis_client is None and settings.redis_url:
        try:
            redis_client = redis.from_url(settings.redis_url)
        except Exception as e:
            print(f"Redis connection failed: {e}")
    return redis_client

# Temp directory for work
WORK_DIR = os.path.join(tempfile.gettempdir(), "lazydev_jobs")


async def queue_job(job_id: str):
    """Add job to Redis queue for processing"""
    client = get_redis()
    if client:
        try:
            client.rpush("lazydev:jobs", job_id)
        except Exception as e:
            print(f"Failed to queue job {job_id}: {e}")
    else:
        print(f"Redis unavailable, job {job_id} saved to DB only")


async def get_db_client():
    """Get MongoDB client for worker"""
    client = AsyncIOMotorClient(settings.mongodb_uri)
    return client.lazydev


async def process_job(job_id: str):
    """Process a single job - execute all commits with delays"""
    db = await get_db_client()
    job = await db.jobs.find_one({"id": job_id})
    
    if not job:
        print(f"Job {job_id} not found")
        return
    
    if job["status"] == JobStatus.CANCELLED:
        print(f"Job {job_id} was cancelled")
        return
    
    # Update job status to in_progress
    await db.jobs.update_one(
        {"id": job_id},
        {"$set": {"status": JobStatus.IN_PROGRESS, "started_at": datetime.utcnow()}}
    )
    
    # Setup working directory
    job_work_dir = os.path.join(WORK_DIR, job_id)
    zip_path = os.path.join(job_work_dir, "source.zip")
    extract_dir = os.path.join(job_work_dir, "source")
    
    try:
        # Download zip from R2
        os.makedirs(job_work_dir, exist_ok=True)
        await download_from_r2(job["zip_key"], zip_path)
        
        # Extract zip
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        # Handle nested directory (if zip contains a single root folder)
        contents = os.listdir(extract_dir)
        if len(contents) == 1 and os.path.isdir(os.path.join(extract_dir, contents[0])):
            extract_dir = os.path.join(extract_dir, contents[0])
        
        # Setup git
        success, msg = setup_git_repo(extract_dir, job["repo"])
        if not success:
            raise Exception(msg)
        
        # Process each commit
        commits = job["commits"]
        for i, commit in enumerate(commits):
            # Check if job was cancelled
            job = await db.jobs.find_one({"id": job_id})
            if job["status"] == JobStatus.CANCELLED:
                print(f"Job {job_id} cancelled during execution")
                break
            
            # Wait for delay
            if commit["delay_mins"] > 0:
                await asyncio.sleep(commit["delay_mins"] * 60)
            
            # Check again after delay
            job = await db.jobs.find_one({"id": job_id})
            if job["status"] == JobStatus.CANCELLED:
                break
            
            # Update commit status
            commits[i]["status"] = CommitStatus.IN_PROGRESS
            await db.jobs.update_one(
                {"id": job_id},
                {"$set": {"commits": commits}}
            )
            
            # Execute commit
            success, msg = commit_files(extract_dir, commit["files"], commit["message"])
            
            if not success:
                if "No files found" in msg:
                    # Skip this commit
                    commits[i]["status"] = CommitStatus.SKIPPED
                    commits[i]["error"] = msg
                    await send_commit_notification(job["repo"], commit["message"], "skipped")
                else:
                    # Commit failed
                    commits[i]["status"] = CommitStatus.FAILED
                    commits[i]["error"] = msg
                    await send_commit_notification(job["repo"], commit["message"], "failed", msg)
            else:
                # Push to remote
                push_success, push_msg = push_to_remote(extract_dir)
                if push_success:
                    commits[i]["status"] = CommitStatus.COMPLETED
                    commits[i]["committed_at"] = datetime.utcnow()
                    await send_commit_notification(job["repo"], commit["message"], "completed")
                else:
                    commits[i]["status"] = CommitStatus.FAILED
                    commits[i]["error"] = push_msg
                    await send_commit_notification(job["repo"], commit["message"], "failed", push_msg)
            
            # Update job with commit status
            completed = sum(1 for c in commits if c["status"] == CommitStatus.COMPLETED)
            await db.jobs.update_one(
                {"id": job_id},
                {"$set": {"commits": commits, "completed_commits": completed}}
            )
        
        # Job complete
        job = await db.jobs.find_one({"id": job_id})
        if job["status"] != JobStatus.CANCELLED:
            completed = sum(1 for c in job["commits"] if c["status"] == CommitStatus.COMPLETED)
            failed = sum(1 for c in job["commits"] if c["status"] == CommitStatus.FAILED)
            
            final_status = JobStatus.COMPLETED if failed == 0 else JobStatus.FAILED
            await db.jobs.update_one(
                {"id": job_id},
                {"$set": {"status": final_status, "finished_at": datetime.utcnow()}}
            )
            await send_job_complete_notification(job["repo"], job["total_commits"], completed, final_status)
    
    except Exception as e:
        print(f"Job {job_id} failed: {e}")
        await db.jobs.update_one(
            {"id": job_id},
            {"$set": {
                "status": JobStatus.FAILED,
                "error": str(e),
                "finished_at": datetime.utcnow()
            }}
        )
        await send_job_complete_notification(job["repo"], job["total_commits"], job["completed_commits"], "failed")
    
    finally:
        # Cleanup
        try:
            await delete_from_r2(job["zip_key"])
            if os.path.exists(job_work_dir):
                shutil.rmtree(job_work_dir)
        except Exception as e:
            print(f"Cleanup error: {e}")


async def resume_incomplete_jobs():
    """Re-queue any jobs that were interrupted (in_progress status)"""
    try:
        db = await get_db_client()
        # Find jobs that are stuck in in_progress
        cursor = db.jobs.find({"status": JobStatus.IN_PROGRESS})
        jobs = await cursor.to_list(length=100)
        
        client = get_redis()
        for job in jobs:
            job_id = job["id"]
            print(f"Resuming interrupted job: {job_id}")
            if client:
                client.rpush("lazydev:jobs", job_id)
            else:
                # Process directly if Redis unavailable
                await process_job(job_id)
        
        if jobs:
            print(f"Resumed {len(jobs)} interrupted job(s)")
    except Exception as e:
        print(f"Error resuming jobs: {e}")


async def run_worker():
    """Main worker loop - process jobs from Redis queue"""
    print("LazyDev Worker started...")
    
    # Resume any jobs that were interrupted by restart
    await resume_incomplete_jobs()
    
    while True:
        try:
            client = get_redis()
            if not client:
                print("Redis not available, waiting...")
                await asyncio.sleep(10)
                continue
            
            # Run blocking Redis call in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: client.blpop("lazydev:jobs", timeout=5))
            if result:
                _, job_id = result
                job_id = job_id.decode('utf-8')
                print(f"Processing job: {job_id}")
                await process_job(job_id)
        except Exception as e:
            print(f"Worker error: {e}")
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(run_worker())
