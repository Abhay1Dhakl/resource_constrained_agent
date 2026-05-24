# Resource-Constrained Agent

A resource-constrained ReAct agent for the assignment planning loop. The agent operates under a hard budget of 10 LLM calls and $0.20 per task, uses exactly three tools, and records a trace of planning, tool use, reflection, and replanning decisions.

## Run

This project targets **Python 3.11+**. If your system `python3` is older, use a
Python 3.11 interpreter explicitly or run the containerized path instead.

### Environment

Create a `.env` file from `.env.example` and fill in the required API keys:

```bash
cp .env.example .env
```

Required variables:

- `OPENAI_API_KEY`: required for the planner LLM
- `TAVILY_API_KEY`: required for live web search tasks

Optional variables:

- `OPENAI_MODEL`
- `OPENAI_REASONING_EFFORT`
- `OPENAI_INPUT_COST_PER_MILLION`
- `OPENAI_OUTPUT_COST_PER_MILLION`

If `TAVILY_API_KEY` is missing, the web-search tool returns a structured error and web-dependent tasks may partially complete or stop early.

### Virtual Environment Activation

Create the virtual environment with Python 3.11+:

```bash
python3.11 -m venv .venv
```

Activate it with the command that matches your shell:

- macOS/Linux (`bash` or `zsh`):

  ```bash
  source .venv/bin/activate
  ```

- macOS/Linux (`fish`):

  ```fish
  source .venv/bin/activate.fish
  ```

- Windows PowerShell:

  ```powershell
  .venv\Scripts\Activate.ps1
  ```

- Windows Command Prompt:

  ```cmd
  .venv\Scripts\activate.bat
  ```

### Local Run

```bash
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e .
resource-agent
```

### Local Demo UI

If you want a browser-based demo URL, run the Streamlit wrapper locally first:

```bash
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
streamlit run streamlit_app.py
```

The app will open locally in your browser and provides a demo personal profile
by default. You can also upload a PDF resume and convert it into the expected
profile JSON, or edit/upload the profile JSON directly for the current session,
then run the agent and inspect the full trace and budget summary.

### Docker Run

The repository includes a `Dockerfile` and `docker-compose.yml`. After creating `.env`, run:

```bash
docker compose up --build
```

That build uses the local source tree, installs the package in editable mode inside the container, injects variables from `.env`, and runs the evaluation scenarios through the `resource-agent` entrypoint.

You can also build and run directly with Docker:

```bash
docker build -t resource-constrained-agent .
docker run --rm --env-file .env resource-constrained-agent
```

### Tests

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

Run that command from the activated Python 3.11+ virtual environment shown
above.

## Architecture Overview

The system is centered on `ReactAgent`, which orchestrates a loop of: inspect current state, ask the LLM for the next structured decision, enforce the LLM budget, run one of three tools, record the observation, and continue until the agent either produces a final answer or stops. Runtime state is stored in `AgentState`, tool implementations are exposed through `ToolRegistry`, and the OpenAI planner interface is isolated in `OpenAILLMClient`.

The three tools are:

- `web_search_tool`: Tavily-backed web search with bounded `max_results`, topic validation, and timeout handling
- `code_execution_tool`: restricted Python subprocess execution with AST-based checks and timeout enforcement
- `personal_profile_tool`: profile retrieval from local JSON with optional section filtering and timeout handling

## Planning Loop

I chose a ReAct-style loop because it is the simplest way to keep the planner, tool calls, and trace output explicit under a strict budget. Each loop iteration asks the model for a structured decision with one of four statuses: `continue`, `replan`, `final_answer`, or `stop`. The biggest weakness of this approach is that it still depends on the planner to choose useful next steps; even with structured controls, a weak model can still select poor tools or waste early steps before the runtime guardrails intervene.

## Schema Design

The planner returns an `AgentDecision` schema that contains the control fields the loop needs: `thought`, `progress_assessment`, `reason`, `status`, `action`, `action_input`, and `final_answer`. `ActionInput` is a shared envelope for tool arguments such as `query`, `topic`, `max_results`, `code`, `language`, `timeout`, and `section`.

Tool outputs are normalized into a common observation shape with:

- `success`
- `tool_name`
- `data`
- `error`

This lets the loop treat tool results uniformly even when the underlying implementation differs. `AgentState` stores the user task, a list of `AgentStep` entries, replanning events, stop/completion state, and a memory of failed action signatures so repeated fake replans can be blocked.

## Prompt Strategy

The planner instructions explicitly constrain the model to the available tools and require reflection after every observation. Each call receives:

- the user task
- the current scratchpad built from prior steps
- the remaining budget summary
- the available tool list

The prompt pushes the model to:

- choose only known tools
- honor explicit user requests to execute code or use a specific tool when a
  matching tool exists
- mark whether it is making progress
- use `replan` when a failed step is recoverable
- use `stop` when continuing would waste budget
- stay conservative because the task has a hard call and cost budget

The runtime does not rely only on prompt wording. It also records `progress_assessment`, stores replanning events, blocks repeated failed replan attempts, and stops cleanly when budget charging fails.

## Failure Modes

One concrete failure mode observed during development was fake replanning: the planner could label a retry as `replan` while repeating the exact same failed `action` and `action_input`. That created the risk of wasting steps without meaningfully changing strategy. The runtime now records failed action signatures and blocks repeated replanning attempts before rerunning the same failed tool invocation.

Another practical failure mode is that web-search-dependent tasks can only partially complete when `TAVILY_API_KEY` is not available. In that case the web search tool returns a structured error, which is useful for debugging, but it still limits the quality of the final answer.

## Future Work

The biggest known limitation is the code execution tool. It is a restricted subprocess runner with AST-based checks and a timeout, but it is not a true security sandbox. With more time, I would replace it with stronger isolation, such as a dedicated sandboxed runtime or containerized per-execution environment, and add more model-aware pricing configuration plus automated task-result reporting into `test_results.md`.

## Test Results

The repository includes:

- evaluation task definitions in `src/resource_agent/evaluation/tasks.py`
- a task-by-task evaluation report in `test_results.md`
- smoke tests in `tests/`

Current smoke coverage verifies:

- budget overrun stops cleanly
- mid-task budget stop preserves completed progress
- repeated fake replanning is blocked
- successful replanning is recorded
- profile section filtering returns only the requested data
- unknown tool lookup returns a structured error

See also:

- `decisions.md`
- `test_results.md`

## Streamlit Deployment Process

The repository now includes `streamlit_app.py`, which is the fastest path to a
shareable public demo.

Recommended path:

1. Push this repository to GitHub.
2. In Streamlit Community Cloud, create a new app from the repo.
3. Set the entrypoint file to `streamlit_app.py`.
4. Add `OPENAI_API_KEY` and, if you want live web search, `TAVILY_API_KEY` in
   the app secrets as root-level TOML entries, for example:

   ```toml
   OPENAI_API_KEY = "your-openai-key"
   TAVILY_API_KEY = "your-tavily-key"
   ```

5. Deploy and use the generated `*.streamlit.app` URL as your demo link.
6. In the app UI, upload a PDF resume to convert it into profile JSON, or
   replace the default profile JSON manually for that session.

If you do not provide `TAVILY_API_KEY`, the app still runs, but search-heavy
tasks may stop early or return partial results.

The Streamlit PDF flow has two practical caveats:

- Converting a PDF resume into profile JSON uses one additional OpenAI call
  before the agent run, and that conversion call is not counted inside the
  agent's 10-call / $0.20 task budget.
- The PDF converter works best on text-based PDFs. Scanned image-only resumes
  may fail if no readable text can be extracted.
