import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { jobsApi } from "../api/client";
import type { CommitPlan } from "../api/client";

const Upload: React.FC = () => {
  const [zipFile, setZipFile] = useState<File | null>(null);
  const [repo, setRepo] = useState("");
  const [commits, setCommits] = useState<CommitPlan[]>([
    { files: [], message: "", delay_mins: 0 },
  ]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setZipFile(e.target.files[0]);
    }
  };

  const addCommit = () => {
    setCommits([...commits, { files: [], message: "", delay_mins: 30 }]);
  };

  const removeCommit = (index: number) => {
    if (commits.length > 1) {
      setCommits(commits.filter((_, i) => i !== index));
    }
  };

  const updateCommit = (index: number, field: keyof CommitPlan, value: any) => {
    const updated = [...commits];
    if (field === "files") {
      updated[index].files = value
        .split(",")
        .map((f: string) => f.trim())
        .filter(Boolean);
    } else {
      (updated[index] as any)[field] = value;
    }
    setCommits(updated);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!zipFile) {
      setError("Please select a zip file");
      return;
    }
    if (!repo) {
      setError("Please enter a repository name");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const result = await jobsApi.upload(zipFile, { repo, commits });
      navigate(`/jobs/${result.job_id}`);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Upload failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="upload-page">
      <header className="page-header">
        <Link to="/" className="back-link">
          ← Back to Dashboard
        </Link>
        <h1>Create New Job</h1>
      </header>

      <form onSubmit={handleSubmit} className="upload-form">
        <div className="form-section">
          <h3>Project Details</h3>

          <div className="form-group">
            <label htmlFor="repo">Target Repository</label>
            <input
              type="text"
              id="repo"
              placeholder="username/repo-name"
              value={repo}
              onChange={(e) => setRepo(e.target.value)}
              required
            />
            <small>If the repo doesn't exist, LazyDev will create it</small>
          </div>

          <div className="form-group">
            <label htmlFor="zipFile">Project Zip File</label>
            <input
              type="file"
              id="zipFile"
              accept=".zip"
              onChange={handleFileChange}
              required
            />
            {zipFile && <small>Selected: {zipFile.name}</small>}
          </div>
        </div>

        <div className="form-section">
          <div className="section-header">
            <h3>Commit Plan</h3>
            <button type="button" onClick={addCommit} className="add-btn">
              + Add Commit
            </button>
          </div>

          {commits.map((commit, index) => (
            <div key={index} className="commit-card">
              <div className="commit-header">
                <span className="commit-number">Commit #{index + 1}</span>
                {commits.length > 1 && (
                  <button
                    type="button"
                    onClick={() => removeCommit(index)}
                    className="remove-btn"
                  >
                    ✕
                  </button>
                )}
              </div>

              <div className="form-group">
                <label>Files (comma-separated)</label>
                <input
                  type="text"
                  placeholder="file1.py, src/app.js, README.md"
                  value={commit.files.join(", ")}
                  onChange={(e) => updateCommit(index, "files", e.target.value)}
                  required
                />
              </div>

              <div className="form-group">
                <label>Commit Message</label>
                <input
                  type="text"
                  placeholder="Initial setup"
                  value={commit.message}
                  onChange={(e) =>
                    updateCommit(index, "message", e.target.value)
                  }
                  required
                />
              </div>

              <div className="form-group">
                <label>Delay (minutes after previous commit)</label>
                <input
                  type="number"
                  min="0"
                  value={commit.delay_mins}
                  onChange={(e) =>
                    updateCommit(
                      index,
                      "delay_mins",
                      parseInt(e.target.value) || 0
                    )
                  }
                />
              </div>
            </div>
          ))}
        </div>

        {error && <div className="error-message">{error}</div>}

        <button type="submit" disabled={loading} className="submit-btn">
          {loading ? "Creating Job..." : "Create Job"}
        </button>
      </form>
    </div>
  );
};

export default Upload;
