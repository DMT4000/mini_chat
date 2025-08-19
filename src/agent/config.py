import os

# Centralized LLM model selection
# Use a safer default non-reasoning chat model to avoid temperature errors
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")

# Models that do not accept temperature or certain params (reasoning families)
REASONING_MODELS = {"o3", "o3-mini", "gpt-5-mini", "o4-mini-high"}


def llm_kwargs_for(model: str):
    """Return keyword args for ChatOpenAI respecting reasoning models' constraints."""
    if model in REASONING_MODELS:
        # Do not pass temperature to reasoning models
        return {"model": model}
    # Default small temperature for non-reasoning text models
    return {"model": model, "temperature": 0.2}