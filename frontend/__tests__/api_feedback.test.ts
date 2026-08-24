import type { NextApiRequest, NextApiResponse } from "next";
import handler from "../pages/api/feedback";

function createMocks(body: any = {}, method: string = "POST") {
  const req = { method, body } as unknown as NextApiRequest;
  const json = jest.fn();
  const status = jest.fn(() => ({ json }));
  const res = { status } as unknown as NextApiResponse;
  return { req, res, json, status };
}

describe("API /api/feedback", () => {
  const originalFetch = global.fetch;

  afterEach(() => {
    global.fetch = originalFetch;
    jest.restoreAllMocks();
  });

  it("returns 405 on non-POST", async () => {
    const { req, res, status } = createMocks({}, "GET");
    await handler(req, res);
    expect(status).toHaveBeenCalledWith(405);
  });

  it("returns 400 when query_id is missing", async () => {
    const { req, res, status } = createMocks({ score: "up" });
    await handler(req, res);
    expect(status).toHaveBeenCalledWith(400);
  });

  it("submits up and down scores to the backend", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ success: true }),
    }) as unknown as typeof fetch;

    for (const score of ["up", "down"] as const) {
      const { req, res, status, json } = createMocks({
        query_id: "qid-1",
        score,
      });
      await handler(req, res);
      expect(status).toHaveBeenCalledWith(200);
      expect(json).toHaveBeenCalledWith({ success: true });
    }

    expect(global.fetch).toHaveBeenCalledTimes(2);
    const bodies = (global.fetch as jest.Mock).mock.calls.map((call) =>
      JSON.parse(call[1].body),
    );
    expect(bodies[0]).toEqual({ message_id: "qid-1", score: "up" });
    expect(bodies[1]).toEqual({ message_id: "qid-1", score: "down" });
    expect(bodies[0].user_id).toBeUndefined();
  });

  it("does not log prompts or request bodies", async () => {
    const logSpy = jest.spyOn(console, "log").mockImplementation(() => {});
    const errorSpy = jest.spyOn(console, "error").mockImplementation(() => {});
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ success: true }),
    }) as unknown as typeof fetch;

    const { req, res } = createMocks({
      query_id: "qid-1",
      score: "up",
      prompt: "should-not-be-logged",
    });
    await handler(req, res);

    const logged = JSON.stringify([
      ...logSpy.mock.calls,
      ...errorSpy.mock.calls,
    ]);
    expect(logged).not.toContain("should-not-be-logged");
    expect(logged).not.toContain("qid-1");
  });
});
