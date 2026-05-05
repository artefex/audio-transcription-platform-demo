import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, test, vi } from "vitest";
import { TranscriptionDemo } from "../components/TranscriptionDemo";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

function mockFetchOnce(payload: unknown, status = 200) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => payload,
  });
}

test("upload form submits a WAV file", async () => {
  const fetchMock = mockFetchOnce({ job: { id: "job_1", status: "queued" } });
  vi.stubGlobal("fetch", fetchMock);
  render(<TranscriptionDemo />);

  const file = new File(["RIFF....WAVE"], "sample.wav", { type: "audio/wav" });
  await userEvent.upload(screen.getByLabelText("WAV file"), file);
  await userEvent.click(screen.getByRole("button", { name: "Upload WAV" }));

  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
  expect(screen.getByText(/job_1/)).toBeInTheDocument();
});

describe("status rendering", () => {
  test("renders transcript state", async () => {
    vi.stubGlobal(
      "fetch",
      mockFetchOnce({
        job: { id: "job_2", status: "succeeded" },
        transcript: { id: "trn_1", text: "Fake transcript result." },
      }),
    );
    render(<TranscriptionDemo />);

    const file = new File(["RIFF....WAVE"], "sample.wav", { type: "audio/wav" });
    await userEvent.upload(screen.getByLabelText("WAV file"), file);
    await userEvent.click(screen.getByRole("button", { name: "Upload WAV" }));

    expect(await screen.findByLabelText("Transcript")).toHaveTextContent(
      "Fake transcript result.",
    );
  });

  test("renders failed state", async () => {
    vi.stubGlobal(
      "fetch",
      mockFetchOnce({
        job: { id: "job_3", status: "failed", last_error: "provider failed" },
      }),
    );
    render(<TranscriptionDemo />);

    const file = new File(["RIFF....WAVE"], "sample.wav", { type: "audio/wav" });
    await userEvent.upload(screen.getByLabelText("WAV file"), file);
    await userEvent.click(screen.getByRole("button", { name: "Upload WAV" }));

    expect(await screen.findByText(/provider failed/)).toBeInTheDocument();
  });
});
