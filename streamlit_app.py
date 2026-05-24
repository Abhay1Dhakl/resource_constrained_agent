import os

import streamlit as st

from resource_agent.agent.react_agent import ReactAgent
from resource_agent.config import load_env_file
from resource_agent.evaluation.tasks import EVALUATION_TASKS


load_env_file()

st.set_page_config(
    page_title="Resource-Constrained Agent Demo",
    layout="wide",
)


def build_template_map() -> dict[str, str]:
    templates = {"Custom task": ""}
    for evaluation_task in EVALUATION_TASKS:
        label = f"{evaluation_task.name} ({evaluation_task.task_id})"
        templates[label] = evaluation_task.prompt
    return templates


def render_step(step) -> None:
    title = f"Step {step.step_number}"
    if step.action:
        title = f"{title}: {step.action}"

    with st.expander(title, expanded=step.step_number == 1):
        if step.thought:
            st.markdown("**Thought**")
            st.write(step.thought)

        if step.progress_assessment:
            st.markdown("**Progress Assessment**")
            st.write(step.progress_assessment)

        if step.action_input:
            st.markdown("**Action Input**")
            st.json(step.action_input)

        if step.observation:
            st.markdown("**Observation**")
            st.json(step.observation)


def render_result(result: dict) -> None:
    state = result["state"]
    budget = result["budget"]

    st.subheader("Run Summary")
    metric_columns = st.columns(4)
    metric_columns[0].metric("Status", state.status)
    metric_columns[1].metric("Steps", len(state.steps))
    metric_columns[2].metric("LLM Calls", budget["calls_used"])
    metric_columns[3].metric("Cost", f"${budget['total_cost']:.4f}")

    st.markdown("**Stop Reason**")
    st.write(state.stop_reason or "None")

    st.markdown("**Final Answer**")
    st.write(state.final_answer or "No final answer returned.")

    st.subheader("Trace")
    if state.steps:
        for step in state.steps:
            render_step(step)
    else:
        st.info("No steps were executed.")

    if state.replanning_events:
        st.subheader("Replanning Events")
        st.json(state.replanning_events)

    st.subheader("Budget Snapshot")
    st.json(budget)


st.title("Resource-Constrained Agent")
st.caption(
    "Run the agent in a browser, inspect the full ReAct trace, and share a demo URL."
)

templates = build_template_map()
template_labels = list(templates.keys())
default_template = template_labels[1] if len(template_labels) > 1 else template_labels[0]

if "selected_template" not in st.session_state:
    st.session_state.selected_template = default_template

if "task_input" not in st.session_state:
    st.session_state.task_input = templates[default_template]

with st.sidebar:
    st.header("Environment")
    has_openai_key = bool(os.getenv("OPENAI_API_KEY"))
    has_tavily_key = bool(os.getenv("TAVILY_API_KEY"))
    st.write(f"OPENAI_API_KEY: {'configured' if has_openai_key else 'missing'}")
    st.write(f"TAVILY_API_KEY: {'configured' if has_tavily_key else 'missing'}")
    st.caption("OpenAI is required. Tavily is optional but needed for live web search.")

    st.header("Budget")
    max_steps = st.slider("Max steps", min_value=1, max_value=10, value=6)
    max_calls = st.slider("Max LLM calls", min_value=1, max_value=10, value=10)
    max_cost = st.slider("Max cost (USD)", min_value=0.05, max_value=1.00, value=0.20, step=0.05)

left_column, right_column = st.columns([2, 1])

with left_column:
    selected_template = st.selectbox(
        "Prompt template",
        options=template_labels,
        key="selected_template",
    )

    if st.button("Load template"):
        st.session_state.task_input = templates[selected_template]

    st.text_area(
        "Task",
        key="task_input",
        height=220,
        placeholder="Describe what you want the agent to do.",
    )

with right_column:
    st.markdown("**Included Tools**")
    st.write("- `personal_profile_tool`")
    st.write("- `web_search_tool`")
    st.write("- `code_execution_tool`")

if st.button("Run Agent", type="primary"):
    task = st.session_state.task_input.strip()

    if not task:
        st.error("Enter a task before running the agent.")
    elif not has_openai_key:
        st.error("OPENAI_API_KEY is missing. Add it to your environment or Streamlit secrets.")
    else:
        with st.spinner("Running agent..."):
            try:
                agent = ReactAgent(
                    max_steps=max_steps,
                    max_calls=max_calls,
                    max_cost=max_cost,
                )
                state = agent.run(task)
                st.session_state.last_result = {
                    "state": state,
                    "budget": agent.budget_summary(),
                }
            except Exception as exc:
                st.error(f"Agent run failed: {exc}")

if "last_result" in st.session_state:
    render_result(st.session_state.last_result)
