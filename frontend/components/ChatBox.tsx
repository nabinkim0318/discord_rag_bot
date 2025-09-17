// frontend/components/ChatBox.tsx
"use client";

import React, { useState } from "react";

export default function ChatBox() {
  const [input, setInput] = useState("");
  const [response, setResponse] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSend = async () => {
    if (!input.trim()) return;
    setLoading(true);
    try {
      const res = await fetch("/api/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: input }),
      });

      const data = await res.json();
      setResponse(data.response || "No response received.");
    } catch (err) {
      console.error(err);
      setResponse("❌ Error occurred while fetching.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-4">
      <h1 className="text-lg font-bold mb-2">🔍 /api/query Test</h1>
      <input
        className="border px-2 py-1 w-full mb-2"
        type="text"
        placeholder="Type your message here..."
        value={input}
        onChange={(e) => setInput(e.target.value)}
      />
      <button
        onClick={handleSend}
        className="bg-blue-500 text-white px-4 py-1 rounded"
        disabled={loading}
      >
        {loading ? "Loading..." : "Send"}
      </button>
      <div className="mt-4 p-2 border bg-gray-50 rounded">
        <strong>Response:</strong>
        <p>{response}</p>
      </div>
    </div>
  );
}
