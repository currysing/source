import json
import pickle
from pathlib import Path
from datetime import datetime
import jax
import jax.numpy as jnp
from loguru import logger

def init_run_dir(base="outputs"):
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    outdir = Path(base) / f"run_{run_id}"
    outdir.mkdir(parents=True, exist_ok=True)
    return outdir

def save_json(path: Path, obj):
    """Save object as JSON with error handling."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj, indent=2, default=str))
    except Exception as e:
        logger.error(f"Failed to save JSON to {path}: {e}")
        raise

def save_text(path: Path, text: str):
    """Save text to file with error handling."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    except Exception as e:
        logger.error(f"Failed to save text to {path}: {e}")
        raise

def save_policy_params(path: Path, params):
    """Save policy parameters using pickle.
    
    Extracts only the parameter arrays (no closures or function references)
    to ensure successful serialization. Uses JAX tree utilities to safely
    extract only array data.
    
    Note: The inference function is intentionally not saved because it is
    typically a closure and not pickle-serializable. To reload, recreate the
    environment and inference function, then load these params.
    """
    try:
        import numpy as np
        
        def is_array_like(x):
            """Check if x is a JAX or numpy array."""
            return isinstance(x, (jnp.ndarray, jax.Array, np.ndarray))
        
        def extract_arrays_only(p):
            """Recursively extract only array data, converting to numpy.
            
            This function aggressively filters out any non-array objects
            including functions, closures, and other unpicklable objects.
            """
            try:
                if is_array_like(p):
                    # Convert JAX array to numpy and create a copy to avoid view issues
                    arr = np.asarray(p)
                    return arr.copy() if arr.flags.writeable else arr
                elif isinstance(p, dict):
                    # Recursively process dict, only keeping entries with arrays
                    result = {}
                    for k, v in p.items():
                        try:
                            extracted = extract_arrays_only(v)
                            if extracted is not None:
                                result[k] = extracted
                        except (TypeError, AttributeError, ValueError):
                            # Skip entries that can't be processed (functions, closures, etc.)
                            continue
                    return result if result else None
                elif isinstance(p, (list, tuple)):
                    # Recursively process list/tuple
                    extracted = []
                    for v in p:
                        try:
                            result = extract_arrays_only(v)
                            if result is not None:
                                extracted.append(result)
                        except (TypeError, AttributeError, ValueError):
                            # Skip items that can't be processed
                            continue
                    if extracted:
                        # Preserve tuple type if original was tuple
                        return type(p)(extracted) if isinstance(p, tuple) else extracted
                    return None
                elif callable(p) or hasattr(p, '__call__'):
                    # Explicitly skip callable objects (functions, closures)
                    return None
                else:
                    # Skip everything else (functions, closures, etc.)
                    return None
            except (TypeError, AttributeError, ValueError, RuntimeError) as e:
                # If anything goes wrong during extraction, skip this node
                logger.debug(f"Skipping unpicklable object during param extraction: {type(p).__name__}: {e}")
                return None
        
        # Extract only arrays from the params structure
        clean_params = extract_arrays_only(params)
        
        if clean_params is None:
            raise ValueError(
                "No array data found in params structure. "
                "Params may be empty or contain only non-array objects."
            )
        
        # Verify the extracted params are picklable before saving
        try:
            pickle.dumps(clean_params)
        except Exception as pickle_test_error:
            logger.warning(
                f"Extracted params are not directly picklable: {pickle_test_error}. "
                f"Trying alternative serialization approach..."
            )
            # Try using JAX's built-in serialization if available
            # Otherwise, convert to a more basic structure
            def to_serializable(x):
                """Convert to a structure that's definitely serializable."""
                if isinstance(x, np.ndarray):
                    return x.tolist() if x.size < 10000 else x  # Small arrays as lists, large as arrays
                elif isinstance(x, dict):
                    return {k: to_serializable(v) for k, v in x.items()}
                elif isinstance(x, (list, tuple)):
                    converted = [to_serializable(v) for v in x]
                    return type(x)(converted) if isinstance(x, tuple) else converted
                else:
                    return x
            
            clean_params = to_serializable(clean_params)
        
        policy_data = {
            "params": clean_params,
            "serialization": "pickle",
            "inference_fn_saved": False,
            "inference_fn_note": (
                "Inference function not saved. Recreate it using the same "
                "environment/reward setup and load these params."
            ),
        }
        
        with open(path, "wb") as f:
            pickle.dump(policy_data, f)
            
    except Exception as e:
        # If extraction fails, wrap the error with more context
        raise ValueError(
            f"Failed to save policy parameters: {e}. "
            f"This usually means params contains unpicklable objects (closures/functions). "
            f"Try ensuring params only contains arrays/dicts/lists."
        )

def init_leaderboard(outdir: Path):
    lb = outdir / "leaderboard.csv"
    if not lb.exists():
        lb.write_text("iteration,candidate,score,avg_return,artifact_path\n")
    return lb

def append_leaderboard(lb_path, iteration: int, candidate: int, score: float, avg_return: float, artifact_path: str):
    """Append entry to leaderboard CSV with error handling."""
    try:
        lb_path = Path(lb_path)
        lb_path.parent.mkdir(parents=True, exist_ok=True)
        with open(lb_path, "a") as f:
            f.write(f"{iteration},{candidate},{score},{avg_return},{artifact_path}\n")
    except Exception as e:
        logger.error(f"Failed to append to leaderboard {lb_path}: {e}")
        raise

def iteration_dir(outdir, iteration: int):
    p = outdir / f"iteration_{iteration:03d}"
    p.mkdir(parents=True, exist_ok=True)
    return p

def candidate_dir(outdir, iteration: int, candidate: int):
    p = iteration_dir(outdir, iteration) / f"candidate_{candidate:02d}"
    p.mkdir(parents=True, exist_ok=True)
    return p

def load_policy_params(path: Path):
    """Load policy parameters from a saved pickle file.
    
    Args:
        path: Path to the saved policy file (.pkl)
    
    Returns:
        dict with 'params' key containing the loaded parameters, and optionally
        'make_inference_fn' if it was successfully serialized
    """
    path = Path(path)
    
    if path.suffix != '.pkl':
        raise ValueError(f"Expected .pkl file, got {path.suffix}")
    
    with open(path, "rb") as f:
        policy_data = pickle.load(f)
    
    return policy_data
