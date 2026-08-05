# Build Rules

These rules apply to every phase of building this project. Follow them
regardless of which component (agent, API route, UI page, data wrapper) is
being worked on.

## 1. Test after every change
- After adding or modifying any piece of functionality, write and run a test
  for it before moving to the next task — do not batch untested code.
- Prefer a real, runnable check over a hand-wave: a unit test (`pytest`), a
  direct call to the new function/endpoint, or (for API routes) a `curl` /
  Swagger UI hit against `/docs`.
- For agent nodes: test the node in isolation with a known ticker before
  wiring it into the graph.
- For the compiled LangGraph graph: test each flow (`single`, `portfolio`,
  `compare`) end-to-end with at least one real ticker.
- For the UI: manually exercise the feature in the browser (Streamlit) after
  wiring it to the backend — don't declare a UI change done from code review
  alone.
- If a test fails, fix the root cause before continuing — don't comment out
  or skip a failing test to move forward.

## 2. Log everything to `dump.log`
- All runtime logs (info, warnings, errors, agent inputs/outputs, tool calls
  to yfinance/DuckDuckGo, LLM calls) get written to a single `dump.log` file
  at the project root, in addition to console output.
- Use Python's standard `logging` module with two handlers (console +
  `FileHandler("dump.log")`), configured once in one place (e.g.
  `backend/logging_config.py`) and imported everywhere — don't reconfigure
  logging per-module.
- Log at the boundary of every agent/tool call: what was requested, what was
  returned (or the error), and how long it took. This is what makes debugging
  a multi-agent parallel fan-out possible.
- `dump.log` is a local artifact, not a build artifact — it must be
  git-ignored (see below) and should append across runs, not require manual
  clearing.

## 3. Secrets live only in `.env`
- All secret/config values (`GROQ_API_KEY`, any other API keys, ports,
  model names if you want them swappable) go in a `.env` file at the project
  root, loaded via `python-dotenv` (or equivalent) at startup.
- Never hardcode a key or paste a real key into source, tests, prompts, or
  logs.
- Maintain `.env.example` alongside it with the same variable names and
  placeholder values, committed to git so the shape of required config is
  documented — `.env` itself is never committed.

## 4. Git hygiene
- `.env` and `dump.log` must be listed in `.gitignore` — never commit either.
- Commit in small, working increments that pass the tests from Rule 1 —
  don't accumulate multiple untested features into one commit.
