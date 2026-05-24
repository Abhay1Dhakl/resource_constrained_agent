## Engineering trade-off I made to build this project 
- I considered counting both tool calls and LLM calls against the 10-call budget but chose to count only LLM calls because the assignment defines the hard limit in terms of LLM calls and monetary spend.
- I considered a more complex planner architecture with separate roles but chose a single ReAct-style loop because it is easier to trace and fit within the assignment time budget.
- I considered relying on prompt-only reflection but chose to store progress assessments and replanning events in agent state because the assignment requires visible evidence that replanning actually happened.
