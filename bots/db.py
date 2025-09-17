# bots/db.py
import os
import uuid
from contextlib import contextmanager

import psycopg2


@contextmanager
def conn():
    cn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        yield cn
    finally:
        cn.close()


def insert_message(id, user_id, channel_id, question, private=False):
    with conn() as c:
        cur = c.cursor()
        cur.execute(
            """
            INSERT INTO user_messages (id, user_id, channel_id, question, private)
            VALUES (%s,%s,%s,%s,%s)
        """,
            (id, user_id, channel_id, question, private),
        )
        c.commit()


def update_message_response(
    id,
    response=None,
    discord_message_id=None,
    latency_ms=None,
    status="success",
    error=None,
):
    with conn() as c:
        cur = c.cursor()
        cur.execute(
            """
            UPDATE user_messages
               SET response = COALESCE(%s, response),
                   discord_message_id = COALESCE(%s, discord_message_id),
                   latency_ms = COALESCE(%s, latency_ms),
                   status = %s,
                   error = %s
             WHERE id = %s
        """,
            (response, discord_message_id, latency_ms, status, error, id),
        )
        c.commit()


def insert_feedback(message_id, user_id, score, comment=None):
    with conn() as c:
        cur = c.cursor()
        cur.execute(
            """
            INSERT INTO feedback (id, message_id, user_id, score, comment)
            VALUES (%s,%s,%s,%s,%s)
        """,
            (str(uuid.uuid4()), message_id, user_id, score, comment),
        )
        c.commit()
