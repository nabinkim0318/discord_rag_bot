// frontend/pages/useChat.ts
import { useState } from "react";

export function useChat() {
  const [messages, setMessages] = useState<
    { role: "user" | "bot"; message: string }[]
  >([]);
  const [loading, setLoading] = useState(false);
  const [lastPrompt, setLastPrompt] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const sendMessage = async (prompt: string) => {
    setMessages((prev) => [...prev, { role: "user", message: prompt }]);
    setLoading(true);
    setLastPrompt(prompt);
    setError(null);

    try {
      const response = await fetch("/api/query", {
        method: "POST",
        body: JSON.stringify({ prompt: prompt }),
        headers: { "Content-Type": "application/json" },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          errorData?.error || `server error (${response.status})`,
        );
      }

      const data = await response.json();
      setMessages((prev) => [...prev, { role: "bot", message: data.response }]);
    } catch (err) {
      console.error("Chat error:", err);
      const errorMessage =
        "⚠️ I can't answer your question right now. Please try again later.";
      setMessages((prev) => [...prev, { role: "bot", message: errorMessage }]);
      setError(
        (err as Error)?.message || "Unexpected error. Please try again later.",
      );
    } finally {
      setLoading(false);
    }
  };

  const retryLast = async () => {
    if (loading || !lastPrompt) return;
    await sendMessage(lastPrompt);
  };

  return { messages, loading, sendMessage, retryLast, error, setError };
}
