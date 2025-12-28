from lucas.rl.ppo import PPOPipeline
from lucas import workflow, Workflow
from lucas.actorc.actor import ActorExecutor, ActorFunction, ActorContext, ActorRuntimeClass
from stable_baselines3 import PPO

context = ActorContext.createContext()

ppo_pipeline = PPOPipeline(PPO("MlpPolicy", "CartPole-v1", verbose=1))
ppo_pipeline.set_wrapper(ActorRuntimeClass)
ppo_pipeline.set_dependency(['stable-baselines3', 'gym'])
ppo_pipeline.set_provider('actor')
ppo_pipeline.set_name('ppo_trainer')
ppo_pipeline.set_venv('conda')

@workflow(executor=ActorExecutor, provider='actor')
def ppo_workflow(wf: Workflow):
    _in = wf.input()
    ppo_trainer = ppo_pipeline.export().export()
    ppo = wf.call_method(ppo_trainer, 'train', {'total_timesteps': _in['total_timesteps']})
    return ppo

workflow_func = ppo_workflow.export()
workflow_func({'total_timesteps': 10000})