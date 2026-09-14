from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
load_dotenv()

def pick_llm(level: str):
    """
    Picks the appropriate LLM based on the level of the question.

    Args:
        level (str): The level of question can be "easy", "medium" or "hard".

    Returns:
        str: The name of the LLM to be used.
    """

    if level.lower() == "low":
        llm = ChatOpenAI(model="gpt-5.6-luna",temperature=0)
    elif level.lower() == "medium":
        llm = ChatOpenAI(model="gpt-5.6-terra",temperature=0)
    elif level.lower() == "high":
        llm = ChatOpenAI(model="gpt-5.6-sol",temperature=0)
    else:
        raise ValueError(f"Unsupported level: {level}")

    return llm

