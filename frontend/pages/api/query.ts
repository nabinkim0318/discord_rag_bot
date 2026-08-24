// pages/api/query.ts (for Next.js Pages Router)
import type { NextApiRequest, NextApiResponse } from "next";

const USER_FACING_UNAVAILABLE =
  "The assistant is temporarily unavailable. Please try again.";
const USER_FACING_INVALID = "Invalid question. Please check your input.";
const MAX_PROMPT_LENGTH = 8000;

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
    const prompt = req.body?.prompt;

    if (!isNonEmptyString(prompt)) {
      return res.status(400).json({
        error: "invalid request. prompt is required",
      });
    }

    if (prompt.length > MAX_PROMPT_LENGTH) {
      return res.status(400).json({ error: USER_FACING_INVALID });
    }

    const backendUrl = process.env.BACKEND_URL || "http://api:8001";
    const backendRes = await fetch(`${backendUrl}/api/query/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: prompt, top_k: 5 }),
    });

    if (!backendRes.ok) {
      const status = backendRes.status;
      if (status === 422) {
        return res.status(422).json({ error: USER_FACING_INVALID });
      }
      if (status >= 400 && status < 600) {
        return res.status(status).json({ error: USER_FACING_UNAVAILABLE });
      }
      return res.status(502).json({ error: USER_FACING_UNAVAILABLE });
    }

    const data = await backendRes.json();

    return res.status(200).json({
      response: data.answer || "no response",
      query_id: data.query_id || null,
    });
  } catch {
    return res.status(500).json({
      error: USER_FACING_UNAVAILABLE,
    });
  }
}
