"use client";

type FeedbackStatus = "idle" | "submitting" | "success" | "error";

type Props = {
  onFeedback: (type: "like" | "dislike" | "retry") => void;
  queryId?: string | null;
  disabled?: boolean;
  status?: FeedbackStatus;
};

export default function FeedbackButtons({
  onFeedback,
  queryId,
  disabled = false,
  status = "idle",
}: Props) {
  const canSubmitFeedback =
    Boolean(queryId) && !disabled && status !== "submitting";

  return (
    <div className="flex flex-col gap-1 mt-2">
      <div className="flex gap-3">
        <button
          type="button"
          onClick={() => onFeedback("like")}
          disabled={!canSubmitFeedback}
          aria-label="Thumbs up"
          className="text-xl hover:scale-110 disabled:opacity-40 disabled:hover:scale-100"
        >
          👍
        </button>
        <button
          type="button"
          onClick={() => onFeedback("dislike")}
          disabled={!canSubmitFeedback}
          aria-label="Thumbs down"
          className="text-xl hover:scale-110 disabled:opacity-40 disabled:hover:scale-100"
        >
          👎
        </button>
        <button
          type="button"
          onClick={() => onFeedback("retry")}
          aria-label="Retry"
          className="text-xl hover:scale-110"
        >
          🔁
        </button>
      </div>
      {status === "success" && (
        <p className="text-xs text-green-700">Thanks for the feedback.</p>
      )}
      {status === "error" && (
        <p className="text-xs text-red-700">Could not save feedback.</p>
      )}
      {!queryId && status === "idle" && (
        <p className="text-xs text-gray-500">
          Feedback unavailable for this reply.
        </p>
      )}
    </div>
  );
}
