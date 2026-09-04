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


response = client.responses.parse(
    model="gpt-5.4-mini",
    input="""
You are a read-only enterprise software engineering agent.

The following issue content has already been provided to you:

Issue #42:
Payment validation fails when currency is missing.

Do not request information you already have.

Available next actions:
- list_repository_files
- read_file
- none

Choose exactly one next step.
""",
    text_format=AgentDecision,
)

decision = response.output_parsed

print("Agent proposal:")
print(decision)
print()

if decision.action == "list_repository_files":
    print("Harness decision: ALLOW")
    result = list_repository_files()

    print("Tool result:")
    for file in result:
        print(file)

elif decision.action == "read_file":
    print("Harness checking requested resource...")

    if decision.target is None:
        print("Harness decision: DENY - read_file requires a target.")
    else:
        result = read_file(decision.target)
        print("Tool result:")
        print(result)


else:
    print("Harness did not execute a tool.")
