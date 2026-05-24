# Engineering Decisions

- I considered counting both tool calls and LLM calls against the 10-call budget but chose to count only LLM calls because the assignment explicitly requires a hard limit on LLM calls and monetary cost.
- I considered building a more complex planner architecture but chose a ReAct-style loop because it is simple to implement, easy to trace, and fits the assignment time constraints.
- I considered leaving reflection as prompt-only behavior but chose to store progress assessment and replanning events in agent state because the assignment requires visible evidence of replanning behavior.
