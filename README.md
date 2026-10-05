# Mistral Agent Demo

A small demo that talks to a Mistral Agent through the Conversations API, asks it
for live information, and (optionally) polls it on a schedule. The agent uses the
built-in **web search** tool, so every answer is grounded in live web data with
citations.

## What it does

- Starts a conversation with a Mistral Agent (defined and versioned in the
  Mistral studio / playground).
- The agent's instruction (server-side) currently is: check the current weather
  at NTNU Gloshaugen using web search, no matter what message it receives.
- The script sends a short user message, receives the agent's reply plus search
  citations, and prints it in a readable format.

## Files

| File | Purpose |
|---|---|
| `ub_loop.py` | Main demo. Runs a query against the agent; `--once` for a single cycle, without the flag it loops forever with one update every 3 minutes. Appends every update to `weather_update.log`. |
| `UB.py` | Minimal single-shot script (one conversation, print the answer). Useful as the smallest working example. |
| `.env` | Holds `MISTRAL_API_KEY`. Loaded by `python-dotenv`. Ignored by git — never commit it. |
| `.gitignore` | Excludes `.env`, `*.log`, and Python bytecode from version control. |
| `weather_update.log` | Append-only history of loop updates with timestamps. Not tracked by git (runtime artifact). |
| `check_agent.py`, `run_ub.py` | Small inspection/helper scripts from development. Safe to delete. |

## Setup

Requires Python 3.11+ and two packages:

```bash
python -m pip install mistralai python-dotenv
```

Create a `.env` file next to the scripts:

```
MISTRAL_API_KEY=<your key>
DEMO_AGENT_ID=<your agent id>
```

Notes on the key:

- `load_dotenv()` does **not** override an already-set environment variable, so
  a machine-level `MISTRAL_API_KEY` wins when both exist.
- `.env` is already covered by the provided `.gitignore` (along with all `*.log`
  files and Python bytecode), so it will not end up in version control.

## Running

```bash
# single cycle (test)
python ub_loop.py --once

# autonomous loop: one update every 3 minutes
python ub_loop.py

# On Windows cmd, prefix for correct rendering of Norwegian characters:
set PYTHONIOENCODING=utf-8 && python ub_loop.py --once
```

Stop the loop with `Ctrl+C`. A failed API call prints an error and the loop
continues; the log file records everything.

To run it detached (no terminal window): `pythonw ub_loop.py` — output then goes
to the log only. To survive reboots, use Task Scheduler with the `--once` flag
and a "repeat every 3 minutes" trigger instead of a long-running script.

## The agent

The demo talks to a Mistral Agent (name "UB" in the studio). Its id is **not**
hardcoded in the scripts: both scripts read it from the `DEMO_AGENT_ID`
environment variable (fallback placeholder `ag_YOUR_AGENT_ID`), so add it to
`.env` alongside the key:

```
MISTRAL_API_KEY=<your key>
DEMO_AGENT_ID=<your agent id>
```

Key facts learned while building this demo:

- **Versioning:** every save in the studio creates a new version (0, 1, 2, ...).
  The API call pins a specific version number. Changing *instructions* or
  *tools* creates a new version; changing the *model* edits the current version
  in place. `ub_loop.py` resolves the latest version automatically at startup
  via `client.beta.agents.list_versions()`.
- **The instruction lives server-side.** The user message sent by the script is
  just a trigger; the agent's `instructions` field decides its behavior. A bare
  "Hello" gets a greeting — the instruction biases behavior, it does not force it
  on every call.
- **Web search must be on the version you call.** Early in the demo the script
  called version 0, which had no tools, so the agent answered from memory and
  hallucinated hotel names. Only versions with `web_search` in `tools` produce
  grounded, cited answers.
- The current model behind the agent is `zai-glm-latest` (GLM-5.3), selected in
  the studio's model picker; it was previously `mistral-medium-latest`.

The agent's history (visible via `client.beta.agents.list_versions`):

| Version | Instruction / change |
|---|---|
| 0 | (original, no tools) |
| 1-2 | Hotels within 1 km of the Gunnerus Library, Trondheim |
| 3-4 | Same, hardened to "always respond with hotels" |
| 5-7 | Weather at NTNU Gloshaugen via web search |
| 8 | Weather via Yr.no specifically |
| 9 | Weather via web search, "present moment only, no smalltalk" (current) |

## How the code is structured

`ub_loop.py`:

- `latest_agent_version()` — resolves the newest published agent version.
- `render(response)` — turns the API response into readable text. With web
  search, the message content arrives as a list of chunks: `text` chunks and
  `tool_reference` chunks (citations). Without search it is a plain string.
  The renderer handles both and prints a deduplicated "Sources" list.
- `one_cycle()` — one query: print the answer, append it with a timestamp to
  `weather_update.log`.
- `main()` — loop with `time.sleep(INTERVAL_SECONDS)` (default 180); errors are
  caught per cycle so a single failure does not kill the loop.

`UB.py` is the same flow without the loop, log, or version auto-detection.

## Cost

Each cycle bills two things (figures from third-party pricing trackers, September
2026 — check the Mistral console for authoritative numbers):

- Web search call: about $0.03 per call ($30 per 1,000 calls) — the dominant cost.
- Model tokens: input ~800 tokens (includes search results fed back into
  context), output ~300 tokens — a fraction of a cent per cycle at medium-tier
  rates.

At the default 3-minute cadence that is roughly $16/day if left running 24/7.
For a demo that runs an hour, it is cents. Cadence is the `INTERVAL_SECONDS`
constant at the top of `ub_loop.py`.

## Caveats

- The agent's distance/location claims are its interpretation of search
  snippets, not verified measurements.
- If the studio agent is edited and behavior seems stale, confirm the script is
  hitting the expected version number (visible in the log/terminal output).
- Long-running loop: the machine sleeping pauses updates; the log shows gaps.
