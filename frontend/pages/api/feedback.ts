// pages/api/feedback.ts
import type { NextApiRequest, NextApiResponse } from "next";

const USER_FACING_ERROR = "Could not save feedback. Please try again.";
const USER_FACING_INVALID = "Feedback could not be submitted.";

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse,
) {
  if (req.method !== "POST") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  try {
    const queryId = req.body?.query_id;
    const score = req.body?.score;

    if (!isNonEmptyString(queryId)) {
      return res.status(400).json({ error: USER_FACING_INVALID });
    }
    if (score !== "up" && score !== "down") {
      return res.status(400).json({ error: USER_FACING_INVALID });
    }

    const backendUrl = process.env.BACKEND_URL || "http://api:8001";
    const backendRes = await fetch(`${backendUrl}/api/v1/feedback/submit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message_id: queryId,
        score,
      }),
    });

    if (!backendRes.ok) {
      const status = backendRes.status;
      if (status === 400) {
        return res.status(400).json({ error: USER_FACING_INVALID });
      }
      if (status >= 400 && status < 600) {
        return res.status(status).json({ error: USER_FACING_ERROR });
      }
      return res.status(502).json({ error: USER_FACING_ERROR });
    }

    return res.status(200).json({ success: true });
  } catch {
    return res.status(500).json({ error: USER_FACING_ERROR });
  }
}
