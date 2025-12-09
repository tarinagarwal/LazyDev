import axios from "axios";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface CommitPlan {
  files: string[];
  message: string;
  delay_mins: number;
}

export interface CommitPlanRequest {
  repo: string;
  commits: CommitPlan[];
}

export interface CommitRecord {
  files: string[];
  message: string;
  delay_mins: number;
  status: string;
  error?: string;
  committed_at?: string;
}

export interface Job {
  id: string;
  repo: string;
  status: string;
  total_commits: number;
  completed_commits: number;
  created_at: string;
  started_at?: string;
  finished_at?: string;
  error?: string;
}

export interface JobDetail extends Job {
  commits: CommitRecord[];
}

export const authApi = {
  login: async (data: LoginRequest): Promise<LoginResponse> => {
    const response = await api.post("/login", data);
    return response.data;
  },
};

export const jobsApi = {
  list: async (): Promise<Job[]> => {
    const response = await api.get("/jobs");
    return response.data;
  },

  get: async (id: string): Promise<JobDetail> => {
    const response = await api.get(`/jobs/${id}`);
    return response.data;
  },

  cancel: async (id: string): Promise<void> => {
    await api.post(`/jobs/${id}/cancel`);
  },

  upload: async (
    zipFile: File,
    commitPlan: CommitPlanRequest
  ): Promise<{ job_id: string }> => {
    const formData = new FormData();
    formData.append("zip_file", zipFile);
    formData.append("commit_plan", JSON.stringify(commitPlan));

    const response = await api.post("/upload", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });
    return response.data;
  },
};

export default api;
