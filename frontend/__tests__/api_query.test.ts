import type { NextApiRequest, NextApiResponse } from "next";
import handler from "../pages/api/query";

function createMocks(body: any = {}, method: string = "POST") {
  const req = { method, body } as unknown as NextApiRequest;
  const json = jest.fn();
  const status = jest.fn(() => ({ json }));
  const res = { status } as unknown as NextApiResponse;
  return { req, res, json, status };
}

describe("API /api/query", () => {
  const originalFetch = global.fetch;

  afterEach(() => {
    global.fetch = originalFetch;
    jest.restoreAllMocks();
  });

  it("returns 400 on invalid payload", async () => {
    const { req, res, status, json } = createMocks({});
    await handler(req, res);
    expect(status).toHaveBeenCalledWith(400);
    expect(json).toHaveBeenCalled();
  });

  it("returns 405 on non-POST", async () => {
    const { req, res, status } = createMocks({}, "GET");
    await handler(req, res);
    expect(status).toHaveBeenCalledWith(405);
  });

  it("does not log the request body or prompt", async () => {
    const logSpy = jest.spyOn(console, "log").mockImplementation(() => {});
    const errorSpy = jest.spyOn(console, "error").mockImplementation(() => {});
    const { req, res } = createMocks({ prompt: "secret-user-prompt" });

    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ answer: "ok", query_id: "qid-1" }),
    }) as unknown as typeof fetch;

    await handler(req, res);

    const logged = JSON.stringify([
      ...logSpy.mock.calls,
      ...errorSpy.mock.calls,
    ]);
    expect(logged).not.toContain("secret-user-prompt");
    expect(logged).not.toContain('"prompt"');
  });

  it("preserves query_id from the backend response", async () => {
    const { req, res, json, status } = createMocks({ prompt: "What is RAG?" });
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        answer: "Retrieval-Augmented Generation",
        query_id: "qid-99",
      }),
    }) as unknown as typeof fetch;

    await handler(req, res);

    expect(status).toHaveBeenCalledWith(200);
    expect(json).toHaveBeenCalledWith({
      response: "Retrieval-Augmented Generation",
      query_id: "qid-99",
    });
  });

  it("returns a stable error without forwarding backend details", async () => {
    const { req, res, json, status } = createMocks({ prompt: "What is RAG?" });
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 503,
      json: async () => ({
        message: "provider secret: invalid credential",
        detail: "stack-trace",
      }),
    }) as unknown as typeof fetch;

    await handler(req, res);

    expect(status).toHaveBeenCalledWith(503);
    const payload = json.mock.calls[0][0];
    expect(payload.error).toBe(
      "The assistant is temporarily unavailable. Please try again.",
    );
    expect(JSON.stringify(payload)).not.toContain("provider secret");
    expect(JSON.stringify(payload)).not.toContain("stack-trace");
  });
});
