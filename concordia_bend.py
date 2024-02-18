import json
from typing import List
#from gpt_language import gptmodel
from openai import OpenAI

api_key = ''
GPT_MODEL_NAME = 'gpt-4-turbo-preview'

client = OpenAI(api_key='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') # does this api key work?


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

    response = json.loads(
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
        )
    )["insurance_plans"]

    try:
        assert len(response) == 3
        for i in response:
            assert len(i) == 3
            for k in i:
                assert type(k) == int
    except AssertionError:
        insurance_plans = [
            (0, 100, 10),  # premium, coverage, deductible
            (100, 1000, 200),
            (4000, 100_000, 0),
        ]
    raise NotImplementedError


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

def get_all_actions(state, user_bkgrd):
    pass 


def simulate_with_agents(env, user_bkgrd, num_iterations=10):
    state = env.reset()
    history = [state]
    for i in range(num_iterations):
        actions = get_all_actions(state, user_bkgrd)# this should call concordia stuff, all actions for all users.
        state = env.step(state, actions)
        history.append(state)
    
    user_feedback = []

    for j in range(len(user_bkgrd)):
        prompt = 'For' + user_bkgrd[j] + 'with the past history' + history + ', what is good and bad for the user given the history? What has the user learnt?. Use 100 tokens or less.'
        user_feedback.append(client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
            {"role": "system", "content": prompt}
        ],
            max_tokens=100
            ).choices[0].message.content)

        # user_feedback.append(model.sample_text('For:\n'
        #                               + '\n'.join(user_bkgrd[j])
        #                               + 'with the past history'
        #                               + '\n'.join(history) + '\n' 
        #                               + 'what is good and bad for the user given the history? What has the user learnt?'))
     # just create a prompt  here like: giving that you are user_bkgrd[i], what is good and bad for you about history? what have you learned about yourself?
    #user_feedback = # get_feedback(user_bkgrd, history)
    return user_feedback, history

    
def summarize_insights(past_game_history):
    # GPT_API_KEY = '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'
    # GPT_MODEL_NAME = 'gpt-4'
    # model = gptmodel.GptLanguageModel(api_key=GPT_API_KEY, model_name=GPT_MODEL_NAME)
    # shared_context = model.sample_text(
    # 'Please summarize the most salient points of:\n'
    # + '\n'.join(past_game_history)
    # + '\n'
    # + 'Summary:'
    # )
    # return shared_context
    prompt = 'Please summarize the most salient points of:' + past_game_history + 'Do not use more than 100 tokens. Summary:'
    print(prompt)
    response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
            {"role": "system", "content": "You will summarise saliently." + prompt}
        ],
            max_tokens=100
            ).choices[0].message.content
    return response


#     # return llm.call(f"Please summarize the most salient points of {past_game_history}")
# print(summarize_insights("this game is about picking apples. there's a lot of apples to pick."))