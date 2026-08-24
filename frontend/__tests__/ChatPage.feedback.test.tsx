import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import ChatPage from "../pages/ChatPage";

const retryLast = jest.fn();

jest.mock("../hooks/useChat", () => ({
  useChat: () => ({
    messages: [
      { role: "user", message: "What is RAG?" },
      {
        role: "bot",
        message: "Retrieval-Augmented Generation",
        queryId: "qid-42",
      },
    ],
    loading: false,
    sendMessage: jest.fn(),
    retryLast,
    error: null,
    setError: jest.fn(),
  }),
}));

describe("ChatPage feedback", () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    retryLast.mockClear();
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ success: true }),
    }) as unknown as typeof fetch;
    Element.prototype.scrollIntoView = jest.fn();
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it("propagates query ID and submits up feedback", async () => {
    render(<ChatPage />);
    fireEvent.click(screen.getByLabelText("Thumbs up"));

    await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(1));
    const [, options] = (global.fetch as jest.Mock).mock.calls[0];
    expect((global.fetch as jest.Mock).mock.calls[0][0]).toBe("/api/feedback");
    expect(JSON.parse(options.body)).toEqual({
      query_id: "qid-42",
      score: "up",
    });
    expect(
      await screen.findByText("Thanks for the feedback."),
    ).toBeInTheDocument();
  });

  it("submits down feedback", async () => {
    render(<ChatPage />);
    fireEvent.click(screen.getByLabelText("Thumbs down"));

    await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(1));
    const [, options] = (global.fetch as jest.Mock).mock.calls[0];
    expect(JSON.parse(options.body).score).toBe("down");
  });

  it("prevents duplicate feedback clicks", async () => {
    render(<ChatPage />);
    fireEvent.click(screen.getByLabelText("Thumbs up"));
    fireEvent.click(screen.getByLabelText("Thumbs up"));

    await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(1));
  });

  it("shows failure UI without exposing backend errors", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      json: async () => ({ error: "provider secret: invalid credential" }),
    }) as unknown as typeof fetch;

    render(<ChatPage />);
    fireEvent.click(screen.getByLabelText("Thumbs up"));

    expect(
      await screen.findByText("Could not save feedback."),
    ).toBeInTheDocument();
    expect(screen.queryByText(/provider secret/)).not.toBeInTheDocument();
  });

  it("retry does not call the feedback API", () => {
    render(<ChatPage />);
    fireEvent.click(screen.getByLabelText("Retry"));
    expect(retryLast).toHaveBeenCalledTimes(1);
    expect(global.fetch).not.toHaveBeenCalled();
  });
});
