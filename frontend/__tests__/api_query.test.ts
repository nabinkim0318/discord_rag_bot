import type { NextApiRequest, NextApiResponse } from 'next';
import handler from '../pages/api/query';

function createMocks(body: any = {}, method: string = 'POST') {
  const req = { method, body } as unknown as NextApiRequest;
  const json = jest.fn();
  const status = jest.fn(() => ({ json }));
  const res = { status } as unknown as NextApiResponse;
  return { req, res, json, status };
}

describe('API /api/query', () => {
  it('returns 400 on invalid payload', async () => {
    const { req, res, status, json } = createMocks({});
    await handler(req, res);
    expect(status).toHaveBeenCalledWith(400);
    expect(json).toHaveBeenCalled();
  });

  it('returns 405 on non-POST', async () => {
    const { req, res, status } = createMocks({}, 'GET');
    await handler(req, res);
    expect(status).toHaveBeenCalledWith(405);
  });
});
