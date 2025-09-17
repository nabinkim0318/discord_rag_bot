// frontend/pages/FeedbackButtons.tsx
"use client";
import React from "react";

type Props = {
    onFeedback: (type: "like" | "dislike" | "retry") => void;
  };

  export default function FeedbackButtons({ onFeedback }: Props) {
    return (
      <div className="flex gap-3 mt-2">
        <button onClick={() => onFeedback("like")} className="text-xl hover:scale-110">👍</button>
        <button onClick={() => onFeedback("dislike")} className="text-xl hover:scale-110">👎</button>
        <button onClick={() => onFeedback("retry")} className="text-xl hover:scale-110">🔁</button>
      </div>
    );
  }
