// frontend/pages/LoadingMessage.tsx
"use client";

export default function LoadingMessage() {
  return (
    <div className="flex justify-start">
      <div className="flex items-start gap-2 max-w-3xl">
        <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center text-white text-sm font-bold flex-shrink-0">
          🤖
        </div>
        <div className="px-4 py-3 rounded-2xl bg-gray-100 text-gray-800 rounded-bl-md">
          <div className="flex items-center gap-2">
            <div className="flex space-x-1">
              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
              <div
                className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                style={{ animationDelay: "0.1s" }}
              ></div>
              <div
                className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                style={{ animationDelay: "0.2s" }}
              ></div>
            </div>
            <span className="text-sm text-gray-600">Generating answer...</span>
          </div>
        </div>
      </div>
    </div>
  );
}
