from typing import Literal
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
        "search_enterprise_knowledge",
        "none",
    ]
    target: str | None
    reason: str
    status: Literal[
        "continue",
        "finished",
        "needs_human",
    ]


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
- search_enterprise_knowledge
- none

Choose exactly one next step.
""",
    text_format=AgentDecision,
)

decision = response.output_parsed

print(decision)
print()
print("Action:", decision.action)
print("Target:", decision.target)
print("Reason:", decision.reason)
print("Status:", decision.status)