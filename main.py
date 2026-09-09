from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel


load_dotenv()

client = OpenAI()


class AgentDecision(BaseModel):
    action: Literal[
        "list_repository_files",
        "read_file",
        "none",
    ]
    target: str | None
    reason: str
    status: Literal[
        "continue",
        "finished",
        "needs_human",
    ]


def list_repository_files() -> list[str]:
    repository_root = Path(".")

    excluded_directories = {
        ".git",
        ".venv",
        "__pycache__",
    }

    excluded_files = {
        ".env",
    }

    files = []

    for path in repository_root.rglob("*"):
        if not path.is_file():
            continue

        if any(part in excluded_directories for part in path.parts):
            continue

        if path.name in excluded_files:
            continue

        files.append(str(path))

    return files


def read_file(target: str) -> str:
    repository_root = Path(".").resolve()
    requested_path = (repository_root / target).resolve()

    # Prevent escaping the repository
    if repository_root not in requested_path.parents:
        return "ERROR: File is outside the repository."

    # Block sensitive files
    if requested_path.name == ".env":
        return "DENIED: Access to .env is prohibited."

    if not requested_path.is_file():
        return "ERROR: File does not exist."

    return requested_path.read_text(encoding="utf-8")


if __name__ == "__main__": 

    MAX_STEPS = 5

    conversation = """
    You are a read-only enterprise software engineering agent.

    Task:
    Issue #42:
    Payment validation fails when currency is missing.

    Available actions:
    - list_repository_files
    - read_file
    - none

    Rules:
    - Choose exactly one next action.
    - Do not request information already present in the observations.
    - Use status "finished" when no further useful action is possible.
    """


    for step in range(MAX_STEPS):
        print(f"\n--- Step {step + 1} ---")

        response = client.responses.parse(
            model="gpt-5.4-mini",
            input=conversation,
            text_format=AgentDecision,
        )

        decision = response.output_parsed

        print("Agent proposal:", decision)

        # Stop condition 1: agent believes task is finished
        if decision.status == "finished":
            print("Harness: Agent finished.")
            break

        # Stop condition 2: agent requests human assistance
        if decision.status == "needs_human":
            print("Harness: Human assistance required.")
            break

        # Tool 1: list repository files
        if decision.action == "list_repository_files":
            print("Harness decision: ALLOW")

            files = list_repository_files()
            result = "\n".join(files)

        # Tool 2: read a repository file
        elif decision.action == "read_file":
            if decision.target is None:
                result = "DENIED: read_file requires a target."
            else:
                result = read_file(decision.target)

        # No executable action
        else:
            print("Harness: No executable action.")
            break

        print("Tool result:")
        print(result)

        # Feed the observation back into the context
        # so the next LLM call can reason about it.
        conversation += f"""

    Agent chose:
    {decision.action}

    Target:
    {decision.target}

    Tool observation:
    {result}
    """

    # Stop condition 3: deterministic harness limit
    else:
        print(f"\nHarness: Maximum of {MAX_STEPS} steps reached.")