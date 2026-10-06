import os
import sys
import time
from datetime import datetime

from dotenv import load_dotenv
from mistralai.client import Mistral

load_dotenv()

client = Mistral(api_key=os.environ.get("MISTRAL_API_KEY"))

AGENT_ID = os.environ.get("DEMO_AGENT_ID", "ag_YOUR_AGENT_ID")


def latest_agent_version(agent_id):
    versions = list(client.beta.agents.list_versions(agent_id=agent_id))
    return max(v.version for v in versions)


try:
    AGENT_VERSION = latest_agent_version(AGENT_ID)
except Exception as e:
    print(f"Error: could not resolve agent version for {AGENT_ID}: "
          f"{type(e).__name__}: {e}")
    print("Check your API key, network connection, and DEMO_AGENT_ID.")
    sys.exit(1)

QUERY = "Update"
INTERVAL_SECONDS = 180
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "weather_update.log")


def render(response):
    lines = []
    sources = []
    for entry in response.outputs:
        if entry.type != "message.output":
            continue
        if isinstance(entry.content, str):
            lines.append(entry.content)
            continue
        for chunk in entry.content:
            if chunk.type == "text":
                lines.append(chunk.text)
            elif chunk.type == "tool_reference" and chunk.url not in [u for _, u in sources]:
                sources.append((chunk.title, chunk.url))
    if sources:
        lines.append("\n\nSources:\n")
        lines.extend(f"\n- {t}\n  {u}" for t, u in sources)
    return "".join(lines)


def one_cycle():
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"===== Update {stamp} =====")
    response = client.beta.conversations.start(
        agent_id=AGENT_ID,
        agent_version=AGENT_VERSION,
        inputs=[{"role": "user", "content": QUERY}],
    )
    text = render(response)
    print(text)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n===== Update {stamp} =====\n{text}\n")


def main():
    once = "--once" in sys.argv
    while True:
        try:
            one_cycle()
        except Exception as e:
            print(f"Error: {type(e).__name__}: {e}")
        if once:
            break
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
