import time
from typing import Union

from fastapi import FastAPI
from pydantic import BaseModel
from db.redis import conn as redis
from loguru import logger
from fastapi.middleware.cors import CORSMiddleware
import numpy as np
# import concordia_bend

import concordia

origins = [
    "*",
]
# IMPORTANT REDIS KEYS
# user_ids: List[int]
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



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
    
    state_space, action_space, transition = concordia.get_env(user_bkgrd='No background', user_feedback='No feedback', past_game_history='No history')
    redis.jset('state_space', state_space)
    redis.jset('action_space', action_space)
    redis.jset('transition', transition)
    
    redis.jset("state", {'round':0, 'game_state': []}) 
    


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
    
    state = redis.jget('state')
    state['game_state'].append(redis.jget('state_space'))
    redis.jset('state', state)
    return {"user_id": user_id}


@app.get("/getallusers")
def getallusers():
    users = []
    for user_id in redis.jget("users"):
        users.append(redis.jget(f"user_{user_id}"))
    logger.info(users)
    return {"users": users, "num_users": redis.jget("num_users")}


@app.get("/savechat")
def savechat(user_id: int, chat: str):    
    timestamp = time.time()
    redis.jset(f'chat_{timestamp}_{user_id}', chat)

@app.get('/sendaction')
def sendaction(user_id: int, action: str):    
    timestamp = time.time()
    st = redis.jget("state")

    redis.jset(f"action_{timestamp}_{user_id}_{st['round']}", action)
    
    keys = redis.keys(pattern=f"*_{st['round']}")
    if len(keys) != redis.jget('num_users') :
        return 'Not all actions taken'

    actions = [redis.jget(key) for key in keys]
    transition_function = eval(redis.jget('principal_transition')) 
    
    next_state = transition_function(st['game_state'], actions)
    st['game_state'] = next_state
    redis.jset('state', st)
    
    return next_state
    
@app.get('/sendfeeback')
def sendfeeback(user_id: int, feedback: str):    
    timestamp = time.time()
    redis.jset(f'feedback_{timestamp}_{user_id}', feedback)

@app.get('/optimize')
def optimize():
    # TODO: send the stuff to concordia to process
      #  concordia.process_feedback(user_id, feedback)
    # call into concordia
    pass

@app.get('/getstate')
def getstate(user_id: int):    
    return redis.jget(f'state')['game_state'][user_id]

reset_db()
