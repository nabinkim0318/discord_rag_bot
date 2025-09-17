// frontend/pages/ChatMessage.tsx
"use client";
import React from "react";

type Props = {
  role: "user" | "bot";
  message: string;
};

export default function ChatMessage({ role, message }: Props) {
  return (
    <div className={`flex ${role === "user" ? "justify-end" : "justify-start"} mb-2`}>
      <div
        className={`max-w-md px-4 py-2 rounded-xl shadow ${
          role === "user"
            ? "bg-blue-100 text-right"
            : "bg-gray-100 text-left"
        }`}
      >
        {message}
      </div>
    </div>
  );
}
