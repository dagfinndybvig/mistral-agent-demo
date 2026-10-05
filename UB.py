import os

from dotenv import load_dotenv
from mistralai.client import Mistral

load_dotenv()

client = Mistral(api_key=os.environ.get("MISTRAL_API_KEY"))

inputs = [
    {"role":"user","content":"Hello"}
]

print("Working...")

response = client.beta.conversations.start(
    agent_id=os.environ.get("DEMO_AGENT_ID", "ag_YOUR_AGENT_ID"),
    agent_version=9,
    inputs=inputs,
)

sources = []
for entry in response.outputs:
    if entry.type != "message.output":
        continue
    if isinstance(entry.content, str):
        print(entry.content)
        continue
    for chunk in entry.content:
        if chunk.type == "text":
            print(chunk.text, end="")
        elif chunk.type == "tool_reference" and chunk.url not in [u for _, u in sources]:
            sources.append((chunk.title, chunk.url))

print()
if sources:
    print("\nSources:")
    for title, url in sources:
        print(f"- {title}\n  {url}")