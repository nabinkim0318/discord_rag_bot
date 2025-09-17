// pages/api/query.ts (Next.js Pages Router용)
import type { NextApiRequest, NextApiResponse } from "next";

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  console.log("API route called:", req.method, req.body);

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { prompt } = req.body;

    if (!prompt || typeof prompt !== 'string') {
      return res.status(400).json({
        error: "invalid request. prompt is required"
      });
    }

    console.log("🔍 Received query:", prompt);

    // RAG backend call
    const backendRes = await fetch('http://localhost:8001/api/query/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: prompt, top_k: 5 }),
    });

    if (!backendRes.ok) {
      const errorData = await backendRes.json().catch(() => ({}));
      return res.status(backendRes.status).json({
        error: errorData?.detail || `backend server error (${backendRes.status})`
      });
    }

    const data = await backendRes.json();

    return res.status(200).json({
      response: data.answer || "no response"
    });

  } catch (error) {
    console.error("API route error:", error);
    return res.status(500).json({
      error: "server internal error"
    });
  }
}
