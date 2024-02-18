import redis
import json

conn = redis.Redis(
    host='localhost',
    port=6379,
    charset="utf-8",
    decode_responses=True
)

def jset( key, val):
    conn.set(key, json.dumps(val))

def jget( key):
    if conn.get(key) is None:
        raise KeyError('Key is not in DB')
    return json.loads(conn.get(key))

conn.jset = jset
conn.jget = jget
