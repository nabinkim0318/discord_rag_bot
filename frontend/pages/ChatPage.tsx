// frontend/pages/ChatPage.tsx
import React, { useEffect, useRef, useState } from "react";
import ChatMessage from "./ChatMessage";
import FeedbackButtons from "./FeedbackButtons";
import LoadingMessage from "./LoadingMessage";
import { useChat } from "./useChat";

export default function ChatPage() {
  const { messages, loading, sendMessage } = useChat();
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = () => {
    if (!input.trim() || loading) return;
    sendMessage(input);
    setInput("");
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleFeedback = (type: "like" | "dislike" | "retry") => {
    // TODO: Implement feedback functionality
    console.log("Feedback:", type);
  };

  return (
    <div className="max-w-4xl mx-auto bg-white rounded-lg shadow-lg">
      {/* Chat Header */}
      <div className="bg-blue-600 text-white p-4 rounded-t-lg">
        <h2 className="text-xl font-semibold">🤖 RAG Chat Assistant</h2>
        <p className="text-blue-100 text-sm">
          Enter your question and I'll answer based on the related documents.
        </p>
      </div>

      {/* Messages Area */}
      <div className="h-96 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="text-center text-gray-500 mt-8">
            <p className="text-lg">👋 Hello!</p>
            <p>Ask me anything!</p>
          </div>
        ) : (
          messages.map((msg, i) => (
            <div key={i}>
              <ChatMessage role={msg.role} message={msg.message} />
              {msg.role === "bot" && i === messages.length - 1 && (
                <FeedbackButtons onFeedback={handleFeedback} />
              )}
            </div>
          ))
        )}
        {loading && <LoadingMessage />}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t p-4">
        <div className="flex items-center gap-2">
          <input
            className="flex-1 border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Enter your question... (Enter to send)"
            disabled={loading}
          />
          <button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            className="bg-blue-500 hover:bg-blue-600 disabled:bg-gray-300 text-white px-6 py-2 rounded-lg font-medium transition-colors"
          >
            {loading ? "Sending..." : "Send"}
          </button>
        </div>
        <p className="text-xs text-gray-500 mt-2">
          💡 Enter key to quickly send
        </p>
      </div>
    </div>
  );
}
