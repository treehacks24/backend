import json
import random
from typing import List
# from gpt_language import gptmodel
from openai import OpenAI

client = OpenAI(api_key='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')


def get_env(user_bkgrd: List[str], user_feedback: str, past_game_history: str):
    """
    Note: User feedback can be (values, commments/complaints on env, proposal on env)
    """
    # we just need to prompt the llm here
    prompt = f"""Your goal is to design better insurance plans for seniors. Here are their backgrounds: {user_bkgrd}. Here is how they behave: {past_game_history}. Here is their feedback: {user_feedback}. 
    give me three general simplified insurance plans representative of typical policies for seniors in the u.s. for each insurance plan, give me the premium, coverage, and deductible. just give me numbers for each, formatted like 
    {{"insurance_plans": [
        (0, 100, 10), # premium, coverage, deductible
        (100, 1000, 200), 
        (4000, 100_000, 0)
    ]}}. give no explanations, just the numbers exactly like this in JSON"""

    insurance_plans = json.loads(
        client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {
                    "role": "system",
                    "content": "You are an AI policymaker that outputs in JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        ).choices[0].message.content
    )["insurance_plans"]

    try:
        assert len(insurance_plans) == 3
        for i in insurance_plans:
            assert len(i) == 3
            for k in i:
                assert type(k) == int
    except AssertionError:
        print('prompt failed, falling back to default')
        insurance_plans = [
            (0, 100, 10),  # premium, coverage, deductible
            (100, 1000, 200),
            (4000, 100_000, 0),
        ]
    
    state_space = {
    'netWorth': 100_000, # $
    'healthScore': 100, # 0-100
    'insurancePremium': insurance_plans[0][0], # $
    'insuranceCoverage': insurance_plans[0][1], # $
    'insuranceDeductible': insurance_plans[0][2], # $
    }
    action_space = ['null', 'Switch 0', 'Switch 1', 'Switch 2', 'Work', 'Play', 'Invest']
    
    transition = f"""def transition(state, action):# each step here should be roughly half a year's worth of time
        # TODO make this depend on other agent actions
        insurance_plans = {insurance_plans}
        next_state = []
        for s, a in zip(state, action):
            if a != 'null' and a in action_space:
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
                    if random.uniform(0, 1) > .95:
                        s['healthScore'] -= 50
                        s['healthScore'] = max(0, s['healthScore'])
                    else:
                        s['healthScore'] += 10
                        s['healthScore'] = min(100, s['healthScore'])
                if a == 'Invest':
                    s['netWorth'] += 15_000
                    s['healthScore'] -= 5

            next_state.append(s)
        return next_state"""
            
    return (state_space, action_space, transition)


def optimize(
    user_bkgrd: List[str],
    user_feedback: str,
    past_game_history: str,
    past_environment: List[str],
    num_iterations=1,
):
    """
    Note: User feedback can be (values, commments/complaints on env, proposal on env)
    """
    for i in range(num_iterations):
        env = get_env(
            user_bkgrd=user_bkgrd,
            user_feedback=user_feedback,
            past_game_history=past_game_history,
        )
        user_feedback, past_game_history = simulate_with_agents(
            env, user_bkgrd=user_bkgrd
        )

    return env, summarize_insights(past_game_history)


def simulate_with_agents(env, user_bkgrd, num_iterations=10):
    state = env.reset()
    history = [state]
    for i in range(num_iterations):
        actions = get_all_actions(state, user_bkgrd)  # this should call concordia stuff
        state = env.step(state, actions)
        history.append(state)

    # just create a prompt  here like: giving that you are user_bkgrd[i], what is good and bad for you about history? what have you learned about yourself?
    user_feedback = get_feedback(user_bkgrd, history)
    return user_feedback, history


def summarize_insights(past_game_history):
    GPT_API_KEY = ""  # TODO
    GPT_MODEL_NAME = ""
    model = gptmodel.GptLanguageModel(api_key=GPT_API_KEY, model_name=GPT_MODEL_NAME)
    shared_context = model.sample_text(
        "Please summarize the most salient points of:\n"
        + "\n".join(past_game_history)
        + "\n"
        + "Summary:"
    )
    return shared_context

    # return llm.call(f"Please summarize the most salient points of {past_game_history}")
