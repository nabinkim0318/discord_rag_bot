// frontend/pages/ChatPage.tsx
import React, { useState } from "react";
import ChatMessage from "./ChatMessage";
import LoadingMessage from "./LoadingMessage";
import { useChat } from "./useChat";

export default function ChatPage() {
  const { messages, loading, sendMessage } = useChat();
  const [input, setInput] = useState("");

  const handleSend = () => {
    if (!input.trim()) return;
    sendMessage(input);
    setInput("");
  };

  return (
    <div className="p-6 max-w-xl mx-auto">
      <div className="space-y-3 mb-4">
        {messages.map((msg, i) => (
          <ChatMessage key={i} role={msg.role} message={msg.message} />
        ))}
        {loading && <LoadingMessage />}
      </div>

      <div className="flex items-center gap-2">
        <input
          className="flex-1 border border-gray-300 rounded px-4 py-2"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your message..."
        />
        <button onClick={handleSend} className="bg-blue-500 text-white px-4 py-2 rounded">
          Send
        </button>
      </div>
    </div>
  );
}
