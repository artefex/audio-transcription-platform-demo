import { TranscriptionDemo } from "../components/TranscriptionDemo";

export default function Home() {
  return (
    <main className="page">
      <section className="hero">
        <p className="eyebrow">Public portfolio demo</p>
        <h1>Audio Transcription Platform</h1>
        <p>
          Upload a WAV file, create an idempotent job, let a worker process it with
          the fake provider, and review the transcript result.
        </p>
      </section>
      <TranscriptionDemo />
    </main>
  );
}
