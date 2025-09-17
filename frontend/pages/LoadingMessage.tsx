// frontend/pages/LoadingMessage.tsx
"use client";
import React from "react";

export default function LoadingMessage() {
    return (
      <div className="flex justify-start mb-2">
        <div className="px-4 py-2 rounded-xl bg-yellow-100 text-gray-700 animate-pulse">
          Thinking... 🤔
        </div>
      </div>
    );
  }
