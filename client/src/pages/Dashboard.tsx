import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { jobsApi } from "../api/client";
import type { Job } from "../api/client";
import { useAuth } from "../context/AuthContext";

const Dashboard: React.FC = () => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const { logout } = useAuth();

  const fetchJobs = async () => {
    try {
      const data = await jobsApi.list();
      setJobs(data);
    } catch (err) {
      console.error("Failed to fetch jobs:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
    // Poll for updates every 10 seconds
    const interval = setInterval(fetchJobs, 10000);
    return () => clearInterval(interval);
  }, []);

  const getStatusBadge = (status: string) => {
    const badges: Record<string, string> = {
      pending: "⏳ Pending",
      in_progress: "🔄 In Progress",
      completed: "✅ Completed",
      failed: "❌ Failed",
      cancelled: "🛑 Cancelled",
    };
    return badges[status] || status;
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString();
  };

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>🦥 LazyDev</h1>
        <nav>
          <Link to="/upload" className="nav-btn">
            + New Job
          </Link>
          <button onClick={logout} className="nav-btn logout">
            Logout
          </button>
        </nav>
      </header>

      <main className="dashboard-content">
        <h2>Jobs</h2>

        {loading ? (
          <div className="loading">Loading jobs...</div>
        ) : jobs.length === 0 ? (
          <div className="empty-state">
            <p>No jobs yet. Create your first automated commit job!</p>
            <Link to="/upload" className="create-btn">
              Create Job
            </Link>
          </div>
        ) : (
          <div className="jobs-list">
            {jobs.map((job) => (
              <Link to={`/jobs/${job.id}`} key={job.id} className="job-card">
                <div className="job-header">
                  <span className="job-repo">{job.repo}</span>
                  <span className={`job-status status-${job.status}`}>
                    {getStatusBadge(job.status)}
                  </span>
                </div>
                <div className="job-progress">
                  <div className="progress-bar">
                    <div
                      className="progress-fill"
                      style={{
                        width: `${
                          (job.completed_commits / job.total_commits) * 100
                        }%`,
                      }}
                    />
                  </div>
                  <span className="progress-text">
                    {job.completed_commits}/{job.total_commits} commits
                  </span>
                </div>
                <div className="job-meta">
                  <span>Created: {formatDate(job.created_at)}</span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </main>
    </div>
  );
};

export default Dashboard;
