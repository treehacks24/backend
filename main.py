from typing import Union

from fastapi import FastAPI
from pydantic import BaseModel
from db.redis import conn as redis
from loguru import logger

# IMPORTANT REDIS KEYS
# user_ids: List[int]
import numpy as np
app = FastAPI()


@app.get("/printdb")
def printdb():
    logger.info("printing db")
    for key in redis.keys(pattern="*"):
        logger.info(f"{key} {redis.get(key)}")


@app.get("/reset")
def reset_db():
    for key in redis.keys(pattern="*"):
        redis.delete(key)

    redis.jset("users", [])
    redis.jset("num_users", 0)


@app.get("/createuser")
def createuser(name: str):
    users = redis.jget("users")
    user_id = redis.jget("num_users") + 1

    redis.jset(
        f"user_{user_id}",
        {
            "name": name,
            "lat": 37.42 + np.random.randn() / 100,
            "long": -122.16 + np.random.randn() / 100,
        },
    )
    redis.jset("users", users + [user_id])
    redis.jset("num_users", redis.jget("num_users") + 1)
    return {"user_id": user_id}


@app.get("/getallusers")
def getallusers():
    users = []
    for user_id in redis.jget("users"):
        users.append(redis.jget(f"user_{user_id}"))
    logger.info(users)
    return {"users": users, "num_users": redis.jget("num_users")}


reset_db()
