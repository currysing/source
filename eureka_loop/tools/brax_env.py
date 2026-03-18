import inspect
from brax.envs import create

def get_env_and_source(env_name: str):
    env = create(env_name)
    mod = inspect.getmodule(env.__class__)
    env_source = inspect.getsource(mod)
    return env, env_source, mod.__name__
