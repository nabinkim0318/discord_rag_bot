import { fireEvent, render, screen } from "@testing-library/react";
import ChatPage from "../pages/ChatPage";

jest.mock("../hooks/useChat", () => ({
  useChat: () => ({
    messages: [
      { role: "user", message: "What is RAG?" },
      { role: "bot", message: "hello without an id" },
    ],
    loading: false,
    sendMessage: jest.fn(),
    retryLast: jest.fn(),
    error: null,
    setError: jest.fn(),
  }),
}));

describe("ChatPage feedback without query ID", () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    global.fetch = jest.fn() as unknown as typeof fetch;
    Element.prototype.scrollIntoView = jest.fn();
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it("does not submit feedback when query ID is missing", () => {
    render(<ChatPage />);
    fireEvent.click(screen.getByLabelText("Thumbs up"));
    expect(global.fetch).not.toHaveBeenCalled();
  });
});
