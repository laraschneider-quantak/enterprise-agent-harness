from dotenv import load_dotenv
from openai import OpenAI

# Load variables from the .env file
load_dotenv()

# Create an OpenAI API client
client = OpenAI()

# Send a request to the model
response = client.responses.create(
    model="gpt-5.4-mini",
    input="Explain in one sentence what an enterprise AI agent is."
)

# Print the model's text response
print(response)