import type { Metadata } from "next";
import "./styles.css";

export const metadata: Metadata = {
  title: "Audio Transcription Platform Demo",
  description: "Public-safe async transcription pipeline demo with fake provider default.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
