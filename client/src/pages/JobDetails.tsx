import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { jobsApi } from '../api/client';
import type { JobDetail } from '../api/client';

const JobDetails: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [job, setJob] = useState<JobDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [cancelling, setCancelling] = useState(false);
  const navigate = useNavigate();

  const fetchJob = async () => {
    if (!id) return;
    try {
      const data = await jobsApi.get(id);
      setJob(data);
    } catch (err) {
      console.error('Failed to fetch job:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJob();
    // Poll for updates if job is in progress
    const interval = setInterval(() => {
      if (job?.status === 'pending' || job?.status === 'in_progress') {
        fetchJob();
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [id, job?.status]);

  const handleCancel = async () => {
    if (!id || !window.confirm('Are you sure you want to cancel this job?')) return;
    setCancelling(true);
    try {
      await jobsApi.cancel(id);
      fetchJob();
    } catch (err) {
      console.error('Failed to cancel job:', err);
    } finally {
      setCancelling(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const badges: Record<string, string> = {
      pending: '⏳ Pending',
      in_progress: '🔄 In Progress',
      completed: '✅ Completed',
      failed: '❌ Failed',
      cancelled: '🛑 Cancelled',
      skipped: '⏭️ Skipped',
    };
    return badges[status] || status;
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleString();
  };

  if (loading) {
    return <div className="loading-page">Loading job details...</div>;
  }

  if (!job) {
    return (
      <div className="error-page">
        <h1>Job not found</h1>
        <Link to="/">Back to Dashboard</Link>
      </div>
    );
  }

  const canCancel = job.status === 'pending' || job.status === 'in_progress';

  return (
    <div className="job-details-page">
      <header className="page-header">
        <Link to="/" className="back-link">← Back to Dashboard</Link>
        <h1>Job Details</h1>
      </header>

      <div className="job-info">
        <div className="info-row">
          <span className="label">Repository:</span>
          <a 
            href={`https://github.com/${job.repo}`} 
            target="_blank" 
            rel="noopener noreferrer"
            className="repo-link"
          >
            {job.repo} ↗
          </a>
        </div>
        <div className="info-row">
          <span className="label">Status:</span>
          <span className={`status-badge status-${job.status}`}>
            {getStatusBadge(job.status)}
          </span>
        </div>
        <div className="info-row">
          <span className="label">Progress:</span>
          <div className="progress-inline">
            <div className="progress-bar">
              <div 
                className="progress-fill"
                style={{ width: `${(job.completed_commits / job.total_commits) * 100}%` }}
              />
            </div>
            <span>{job.completed_commits}/{job.total_commits} commits</span>
          </div>
        </div>
        <div className="info-row">
          <span className="label">Created:</span>
          <span>{formatDate(job.created_at)}</span>
        </div>
        <div className="info-row">
          <span className="label">Started:</span>
          <span>{formatDate(job.started_at)}</span>
        </div>
        <div className="info-row">
          <span className="label">Finished:</span>
          <span>{formatDate(job.finished_at)}</span>
        </div>
        {job.error && (
          <div className="info-row error">
            <span className="label">Error:</span>
            <span>{job.error}</span>
          </div>
        )}
      </div>

      {canCancel && (
        <button 
          onClick={handleCancel} 
          disabled={cancelling}
          className="cancel-btn"
        >
          {cancelling ? 'Cancelling...' : 'Cancel Job'}
        </button>
      )}

      <div className="commits-section">
        <h2>Commits</h2>
        <div className="commits-list">
          {job.commits.map((commit, index) => (
            <div key={index} className={`commit-item status-${commit.status}`}>
              <div className="commit-status">
                {getStatusBadge(commit.status)}
              </div>
              <div className="commit-details">
                <div className="commit-message">{commit.message}</div>
                <div className="commit-files">
                  Files: {commit.files.join(', ')}
                </div>
                <div className="commit-meta">
                  {index === 0 ? 'Immediate' : `${commit.delay_mins} min delay`}
                  {commit.committed_at && ` • Committed: ${formatDate(commit.committed_at)}`}
                </div>
                {commit.error && (
                  <div className="commit-error">Error: {commit.error}</div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default JobDetails;
