import ast
import jax
import jax.numpy as jnp
import math

FORBIDDEN_NAMES = {
    "import", "open", "exec", "eval", "__import__", "os", "sys", "subprocess",
    "socket", "shutil", "pathlib"
}

def validate_reward_code(code: str) -> None:
    tree = ast.parse(code)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            raise ValueError("Imports not allowed in reward code.")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in {"exec", "eval", "open", "__import__"}:
                raise ValueError(f"Forbidden call: {node.func.id}")
        if isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
            raise ValueError(f"Forbidden name usage: {node.id}")

def compile_reward(code: str):
    """Compile and validate reward function.
    
    Returns a validated reward function that:
    - Takes (obs, action, next_obs, info) as arguments
    - Returns (total_reward, reward_terms_dict) where:
      - total_reward is a scalar JAX array
      - reward_terms_dict is a dict[str, jnp.ndarray]
    """
    validate_reward_code(code)
    safe_globals = {"jnp": jnp, "jax": jax, "math": math}
    safe_locals = {}
    
    try:
        exec(code, safe_globals, safe_locals)
    except SyntaxError as e:
        raise ValueError(f"Reward code has syntax error: {e}")
    except Exception as e:
        raise ValueError(f"Reward code execution failed: {e}")
    
    if "compute_reward" not in safe_locals:
        raise ValueError("Reward code must define compute_reward().")
    
    reward_fn = safe_locals["compute_reward"]
    
    # Validate function signature by doing a test call
    # This will catch issues early before training
    try:
        # Create dummy inputs with typical shapes
        dummy_obs = jnp.zeros((1, 18))  # Typical HalfCheetah obs shape
        dummy_action = jnp.zeros((1, 6))  # Typical action shape
        dummy_next_obs = jnp.zeros((1, 18))
        dummy_info = {"metrics": {}}
        
        result = reward_fn(dummy_obs, dummy_action, dummy_next_obs, dummy_info)
        
        # Check for None return (common error)
        if result is None:
            raise ValueError(
                "Reward function returned None. "
                "Ensure compute_reward() has a return statement: return total_reward, reward_terms_dict"
            )
        
        # Validate return shape
        if not isinstance(result, tuple):
            raise ValueError(
                f"Reward function must return a tuple (total_reward, reward_terms_dict), "
                f"got {type(result).__name__}. "
                f"Did you forget to return a tuple? Use: return total_reward, reward_terms"
            )
        
        if len(result) != 2:
            raise ValueError(
                f"Reward function must return exactly 2 values (total_reward, reward_terms_dict), "
                f"got {len(result)} values. "
                f"Use: return total_reward, reward_terms"
            )
        
        total_reward, reward_terms = result
        
        # Validate total_reward is a scalar or can be reduced to scalar
        if total_reward is None:
            raise ValueError(
                "total_reward is None. "
                "Ensure you compute and return the total reward value."
            )
        
        if not isinstance(total_reward, (jnp.ndarray, jax.Array)):
            raise ValueError(
                f"total_reward must be a JAX array, got {type(total_reward).__name__}. "
                f"Make sure you're using jnp operations (e.g., jnp.sum(), jnp.mean()) not Python built-ins."
            )
        
        # Validate reward_terms is a dict
        if reward_terms is None:
            raise ValueError(
                "reward_terms is None. "
                "Ensure you create and return a dictionary of reward terms: {{'term_name': value}}"
            )
        
        if not isinstance(reward_terms, dict):
            raise ValueError(
                f"reward_terms must be a dict, got {type(reward_terms).__name__}. "
                f"Use: reward_terms = {{'term_name': value}}"
            )
        
        # Check that reward_terms values are arrays
        for key, value in reward_terms.items():
            if value is None:
                raise ValueError(
                    f"reward_terms['{key}'] is None. "
                    f"Ensure all reward terms are computed before adding to the dict."
                )
            if not isinstance(value, (jnp.ndarray, jax.Array)):
                raise ValueError(
                    f"reward_terms['{key}'] must be a JAX array, got {type(value).__name__}. "
                    f"Use jnp operations to create arrays."
                )
        
    except Exception as e:
        if isinstance(e, ValueError) and ("must return" in str(e) or "must be" in str(e)):
            raise  # Re-raise validation errors
        raise ValueError(
            f"Reward function validation failed (test call error): {e}. "
            f"Ensure compute_reward(obs, action, next_obs, info) returns (scalar, dict)."
        )
    
    return reward_fn
