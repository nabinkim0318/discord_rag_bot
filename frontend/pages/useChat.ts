// frontend/pages/useChat.ts
import { useState } from "react";

export function useChat() {
  const [messages, setMessages] = useState<{ role: "user" | "bot"; message: string }[]>([]);
  const [loading, setLoading] = useState(false);

  const sendMessage = async (prompt: string) => {
    setMessages((prev) => [...prev, { role: "user", message: prompt }]);
    setLoading(true);

    try {
      const response = await fetch("/api/v1/rag", {
        method: "POST",
        body: JSON.stringify({ prompt: prompt  }),
        headers: { "Content-Type": "application/json" },
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data?.error || "Something went wrong");
      }

      setMessages((prev) => [...prev, { role: "bot", message: data.response }]);
    } catch (err) {
      setMessages((prev) => [...prev, { role: "bot", message: "⚠️ Failed to get response." }]);
    } finally {
      setLoading(false);
    }
  };

  return { messages, loading, sendMessage };
}
