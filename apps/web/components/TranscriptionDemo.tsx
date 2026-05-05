"use client";

import { FormEvent, useEffect, useState } from "react";
import { fetchJob, Job, Transcript, uploadAudio } from "../lib/api";

export function TranscriptionDemo() {
  const [file, setFile] = useState<File | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [transcript, setTranscript] = useState<Transcript | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setError("Choose a WAV file first.");
      return;
    }
    setSubmitting(true);
    setError(null);
    setTranscript(null);
    try {
      const response = await uploadAudio(file);
      setJob(response.job);
      setTranscript(response.transcript ?? null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Upload failed.");
    } finally {
      setSubmitting(false);
    }
  }

  useEffect(() => {
    if (!job || job.status === "succeeded" || job.status === "failed") {
      return;
    }
    const interval = window.setInterval(async () => {
      try {
        const response = await fetchJob(job.id);
        setJob(response.job);
        setTranscript(response.transcript ?? null);
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : "Polling failed.");
      }
    }, 1500);
    return () => window.clearInterval(interval);
  }, [job]);

  return (
    <section className="panel" aria-label="Transcription demo">
      <form onSubmit={onSubmit}>
        <div className="form-row">
          <input
            aria-label="WAV file"
            type="file"
            accept="audio/wav,.wav"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          />
          <button type="submit" disabled={submitting}>
            {submitting ? "Uploading..." : "Upload WAV"}
          </button>
        </div>
      </form>

      {job ? (
        <p className="status">
          Job <strong>{job.id}</strong> is <strong>{job.status}</strong>.
        </p>
      ) : (
        <p className="status">No job submitted yet.</p>
      )}

      {error ? <p className="error">{error}</p> : null}
      {transcript ? <pre aria-label="Transcript">{transcript.text}</pre> : null}
      {job?.last_error ? <p className="error">{job.last_error}</p> : null}
    </section>
  );
}
