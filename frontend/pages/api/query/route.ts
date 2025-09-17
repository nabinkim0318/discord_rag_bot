// app/api/query/route.ts (Next.js 13+ App Router용)
import { NextResponse } from "next/server";

export async function POST(req: Request) {
  const body = await req.json();
  const prompt = body.prompt;

  console.log("🔍 Received query:", prompt);

  // RAG backend call
  const res = await fetch('http://localhost:8001/api/v1/rag/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: prompt, top_k: 5 }),
  });

  const data = await res.json();

  return NextResponse.json({
    response: data.answer || "No response received."
  });
}
