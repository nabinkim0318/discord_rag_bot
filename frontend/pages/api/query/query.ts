// pages/api/query.ts
import type { NextApiRequest, NextApiResponse } from "next";

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const { prompt } = req.body;

  try {
    const backendResponse = await fetch("http://localhost:8000/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: prompt }),
    });

    const data = await backendResponse.json();
    return res.status(200).json(data);
  } catch (err) {
    return res.status(500).json({ error: "Backend error" });
  }
}
