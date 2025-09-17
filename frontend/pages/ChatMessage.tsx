// frontend/pages/ChatMessage.tsx
"use client";

type Props = {
  role: "user" | "bot";
  message: string;
};

export default function ChatMessage({ role, message }: Props) {
  return (
    <div
      className={`flex ${role === "user" ? "justify-end" : "justify-start"}`}
    >
      <div className="flex items-start gap-2 max-w-3xl">
        {role === "bot" && (
          <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center text-white text-sm font-bold flex-shrink-0">
            🤖
          </div>
        )}
        <div
          className={`px-4 py-3 rounded-2xl shadow-sm ${
            role === "user"
              ? "bg-blue-500 text-white rounded-br-md"
              : "bg-gray-100 text-gray-800 rounded-bl-md"
          }`}
        >
          <div className="whitespace-pre-wrap break-words">{message}</div>
        </div>
        {role === "user" && (
          <div className="w-8 h-8 bg-gray-400 rounded-full flex items-center justify-center text-white text-sm font-bold flex-shrink-0">
            👤
          </div>
        )}
      </div>
    </div>
  );
}
