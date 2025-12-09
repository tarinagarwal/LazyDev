from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from enum import Enum


class TokenData(BaseModel):
    username: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    username: str
    password: str


class CommitPlan(BaseModel):
    files: List[str]
    message: str
    delay_mins: int = 0


class CommitPlanRequest(BaseModel):
    repo: str
    commits: List[CommitPlan]


class CommitStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


class JobStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CommitRecord(BaseModel):
    files: List[str]
    message: str
    delay_mins: int
    status: CommitStatus = CommitStatus.PENDING
    error: Optional[str] = None
    committed_at: Optional[datetime] = None


class Job(BaseModel):
    id: Optional[str] = None
    repo: str
    zip_key: str  # R2 object key
    commits: List[CommitRecord]
    status: JobStatus = JobStatus.PENDING
    total_commits: int
    completed_commits: int = 0
    created_at: datetime = datetime.utcnow()
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error: Optional[str] = None


class JobResponse(BaseModel):
    id: str
    repo: str
    status: JobStatus
    total_commits: int
    completed_commits: int
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error: Optional[str] = None


class JobDetailResponse(JobResponse):
    commits: List[CommitRecord]
