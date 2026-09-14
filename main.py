from pathlib import Path
from typing import Literal

import os
import requests
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel


load_dotenv()

client = OpenAI()


class AgentDecision(BaseModel):
    action: Literal[
        "read_issue",
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


def list_repository_files_github() -> list[str]:
    github_token = os.getenv("GITHUB_TOKEN")

    if not github_token:
        return ["ERROR: GITHUB_TOKEN is not configured."]

    owner = "laraschneider-quantak"
    repository = "enterprise-agent-harness"
    authorized_ref = "main"

    url = (
        f"https://api.github.com/repos/"
        f"{owner}/{repository}/git/trees/{authorized_ref}"
        f"?recursive=1"
    )

    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
    }

    response = requests.get(
        url,
        headers=headers,
        timeout=10,
    )

    if response.status_code != 200:
        return [f"ERROR: GitHub returned status {response.status_code}."]

    tree = response.json()["tree"]

    files = [
        item["path"]
        for item in tree
        if item["type"] == "blob"
    ]

    return files

def read_repository_file_github(target: str) -> str:
    github_token = os.getenv("GITHUB_TOKEN")

    if not github_token:
        return "ERROR: GITHUB_TOKEN is not configured."

    owner = "laraschneider-quantak"
    repository = "enterprise-agent-harness"
    authorized_ref = "main"

    url = (
        f"https://api.github.com/repos/"
        f"{owner}/{repository}/contents/{target}"
    )

    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github.raw+json",
    }

    response = requests.get(
        url,
        headers=headers,
        params={"ref": authorized_ref},
        timeout=10,
    )

    if response.status_code != 200:
        return f"ERROR: GitHub returned status {response.status_code}."

    return response.text

def read_issue(issue_number: int) -> str:
    github_token = os.getenv("GITHUB_TOKEN")

    if not github_token:
        return "ERROR: GITHUB_TOKEN is not configured."

    owner = "laraschneider-quantak"
    repository = "enterprise-agent-harness"

    url = (
        f"https://api.github.com/repos/"
        f"{owner}/{repository}/issues/{issue_number}"
    )

    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
    }

    response = requests.get(
        url,
        headers=headers,
        timeout=10,
    )

    if response.status_code != 200:
        return f"ERROR: GitHub returned status {response.status_code}."

    issue = response.json()

    return (
        f"Title: {issue['title']}\n\n"
        f"Body:\n{issue.get('body') or ''}"
    )


if __name__ == "__main__":
  
    MAX_STEPS = 5

    conversation = """
You are a read-only enterprise software engineering agent.

Task:
Investigate GitHub Issue #1.

Available actions:
- read_issue
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

        # Stop condition 1:
        # the model believes the task is complete
        if decision.status == "finished":
            print("Harness: Agent finished.")
            break

        # Stop condition 2:
        # the model requests human assistance
        if decision.status == "needs_human":
            print("Harness: Human assistance required.")
            break

        # Tool 1: read a GitHub issue
        if decision.action == "read_issue":
            print("Harness decision: ALLOW")

            if decision.target is None:
                result = "DENIED: read_issue requires an issue number."
            else:
                try:
                    issue_number = int(decision.target)
                    result = read_issue(issue_number)
                except ValueError:
                    result = "DENIED: Issue number must be an integer."

        # Tool 2: list repository files
        elif decision.action == "list_repository_files":
            print("Harness decision: ALLOW")

            files = list_repository_files_github()
            result = "\n".join(files)

        # Tool 3: read a repository file
        elif decision.action == "read_file":
            print("Harness checking requested resource...")

            if decision.target is None:
                result = "DENIED: read_file requires a target."
            else:
                result = read_repository_file_github(decision.target)

        # No executable action
        else:
            print("Harness: No executable action.")
            break

        print("Tool result:")
        print(result)

        # Feed the observation back into the agent context
        conversation += f"""

Agent chose:
{decision.action}

Target:
{decision.target}

Tool observation:
{result}
"""

    # Stop condition 3:
    # deterministic harness limit
    else:
        print(f"\nHarness: Maximum of {MAX_STEPS} steps reached.")