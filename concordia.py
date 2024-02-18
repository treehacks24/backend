import json
import random
from typing import List
from loguru import logger
# from gpt_language import gptmodel
from openai import OpenAI

client = OpenAI(api_key='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')#!! TODO remove

def get_state(insurance_plans):
    idx = random.randint(0, 2)
    state_space = {
    'netWorth': random.randint(0, 5) * 10_000 + 50_000, # $
    'healthScore': 30 + random.randint(0, 63), # 0-100
    'insurancePremium': insurance_plans[idx][0], # $
    'insuranceCoverage': insurance_plans[idx][1], # $
    'insuranceDeductible': insurance_plans[idx][2], # $
    }
    return state_space

action_space = ['Nothing', 'Switch 0', 'Switch 1', 'Switch 2', 'Work', 'Play', 'Invest']

def transition(state, action, insurance_plans, prob_accident=.5):
    next_state = {}
    for s_key, a in zip(state, action):
        s = state[s_key]
        if a != 'Nothing' and a in action_space:
            if 'Switch' in a:
                idx = int(a.split(' ')[-1])
                s['netWorth'] -= 100
                s['insurancePremium'] = insurance_plans[idx][0]
                s['insuranceCoverage'] = insurance_plans[idx][1]
                s['insuranceDeductible'] = insurance_plans[idx][2]
            
            if a == 'Work':
                s['netWorth'] += 30_000
                s['healthScore'] -= 10
            
            if a == 'Play':
                s['healthScore'] += 10
                s['healthScore'] = min(100, s['healthScore'])
            if a == 'Invest':
                s['netWorth'] += 15_000
                s['healthScore'] -= 5
        
        if random.uniform(0, 1) > 1-prob_accident:
            severity = random.uniform(0, 1)
            logger.info(f'Accident with {severity=} for {s_key}!')
            s['healthScore'] -= 100 * severity
            loss = severity * 100_000
            if loss > s['insuranceDeductible']:
                loss -= s['insuranceCoverage']
            
            s['netWorth'] -= loss
            
        s['healthScore'] = int(max(1, s['healthScore']))
        s['netWorth'] -= s['insurancePremium'] * 6

        next_state[s_key] = s
    return next_state

def get_env(user_bkgrd: List[str], user_feedback: str, past_game_history: str, env_params=None):
    """
    Note: User feedback can be (values, commments/complaints on env, proposal on env)
    env_params is insurance_plans
    """
    
    if env_params is None:
        env_params = [
                (100, 10_000, 200),  # premium, coverage, deductible
                (500, 30_000, 1000), 
                (4000, 1_000_000, 0),
            ]
    # we just need to prompt the llm here
    prompt = f"""Your goal is to design better insurance plans for seniors. Here are their backgrounds: {user_bkgrd}. Here is how they behave: {past_game_history}. Here is their feedback: {user_feedback}.
    give me three general simplified insurance plans representative of typical policies for seniors in the u.s. for each insurance plan, give me the premium, coverage, and deductible. just give me numbers for each, formatted like 
    {{"insurance_plans": {env_params}}}. The params mean [(premium, coverage, deductible), (premium, coverage, deductible), (premium, coverage, deductible)]. give no explanations, just the numbers exactly like this in JSON"""

    insurance_plans = None
    # insurance_plans = json.loads(
    #     client.chat.completions.create(
    #         model="gpt-4-turbo-preview",
    #         messages=[
    #             {
    #                 "role": "system",
    #                 "content": "You are an AI policymaker that outputs in JSON.",
    #             },
    #             {"role": "user", "content": prompt},
    #         ],
    #         response_format={"type": "json_object"},
    #     ).choices[0].message.content
    # )["insurance_plans"]

    try:
        assert len(insurance_plans) == 3
        for i in insurance_plans:
            assert len(i) == 3
            for k in i:
                assert type(k) == int
    except:
        print('prompt failed, falling back to default')
        insurance_plans = env_params
    
    state_space = get_state(insurance_plans)
    
    # each step here should be roughly half a year's worth of time
        # TODO make this depend on other agent actions

    return (state_space, action_space, transition, env_params)


def optimize(
    user_bkgrd: List[str],
    user_feedback: str,
    past_game_history: str,
    past_env_params: str,
    num_iterations=1,
):
    """
    Note: User feedback can be (values, commments/complaints on env, proposal on env)
    """
    for i in range(num_iterations):
        logger.info(f'Outer optimization step: {i}')
        env = get_env(
            user_bkgrd=user_bkgrd,
            user_feedback=user_feedback,            
            past_game_history=past_game_history,
            env_params=past_env_params,
        )
        user_feedback, past_game_history = simulate_with_agents(
            env, past_game_history, user_bkgrd=user_bkgrd
        )

    return env, summarize_insights(user_feedback, past_game_history)


def get_all_actions(state, past_game_history, user_bkgrd):
    action_set = []
    for i in range(len(user_bkgrd)):
        prompt = f'Using only 100 tokens, choose an optimal action in {action_space} on {state} given user background {user_bkgrd[i]} and past user behavior {past_game_history}'
        action_set.append(client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
            {"role": "system", "content": prompt}
        ],
            max_tokens=100
            ).choices[0].message.content) # how to get minibatch working here?

    return action_set

def get_all_actions_local(state, user_bkgrd):
    pass

def simulate_with_agents(env, past_game_history, user_bkgrd, num_iterations=3):
    _, _, _, env_params = env

    state = {i: get_state(env_params) for i in range(len(user_bkgrd))}
    history = [state]
    for i in range(num_iterations):
        logger.info(f'>>Inner optimization step: {i}')
        actions = get_all_actions(state, past_game_history, user_bkgrd)# this should call concordia stuff, all actions for all users.
        state = transition(state, actions, env_params)
        # TODO: Check how env.step works        
        history.append(state)
    
    user_feedback = []

    for j in range(len(user_bkgrd)):
        prompt = f'For {user_bkgrd[j]} with the past history {history}, what is good and bad for the user given the history? What has the user learnt?. Use 100 tokens or less.'
        user_feedback.append(client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
            {"role": "system", "content": prompt}
        ],
            max_tokens=100
            ).choices[0].message.content)
    return user_feedback, history
    
def summarize_insights(user_feedback, past_game_history):
    prompt = f'Please summarize the most salient points of: {past_game_history}. Here is the user feedback: {user_feedback}.  Do not use more than 100 tokens. Insight Summary:'
    logger.info(prompt)
    insights = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
            {"role": "system", "content": prompt}
        ],
            max_tokens=100
            ).choices[0].message.content
    return insights


if __name__ == '__main__':
    new_env, insights = optimize(["im a fun gal who hates the government", "the government is the best! but dont make me care about the poor...", "i love the poor, and think insurance is somewhat useful."], "", "", None)
    logger.info(f'insights: {insights}')
