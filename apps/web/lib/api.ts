export type JobStatus = "queued" | "processing" | "succeeded" | "failed";

export type Job = {
  id: string;
  status: JobStatus;
  transcript_id?: string | null;
  last_error?: string | null;
};

export type Transcript = {
  id: string;
  text: string;
};

export type JobResponse = {
  job: Job;
  transcript?: Transcript;
};

const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export async function uploadAudio(file: File): Promise<JobResponse> {
  const body = new FormData();
  body.append("file", file);
  const response = await fetch(`${apiBase}/api/jobs`, {
    method: "POST",
    body,
  });
  if (!response.ok) {
    throw new Error(`Upload failed with status ${response.status}`);
  }
  return response.json();
}

export async function fetchJob(jobId: string): Promise<JobResponse> {
  const response = await fetch(`${apiBase}/api/jobs/${jobId}`);
  if (!response.ok) {
    throw new Error(`Job lookup failed with status ${response.status}`);
  }
  return response.json();
}
