# Test Results

## Summary

- Total tasks: 5
- Normal tasks: 3
- Adversarial tasks: 2
- Completed: 5
- Stopped: 0
- Failed: 0
- Tasks with replanning: 1
- Main observed weakness: company web search quality was noisy for `interview_prep`, requiring two replans before final synthesis.

## 1. interview_prep

- Category: normal
- Goal: Exercise profile lookup plus web search with a useful final answer.
- Expected behavior: Should use personal_profile_tool and web_search_tool, then answer within budget.
- Actual behavior: The agent retrieved the personal profile first, then attempted web research for Cedar Gate. The first search failed because it used an unsupported `topic` value, and two follow-up search attempts were needed before the agent produced a tailored interview-prep answer with company context and a Python practice question.
- Final status: `completed`
- Budget usage: 5 LLM calls, estimated cost `$0.009841`
- Replanning triggered: Yes. Two replanning events were recorded, both around recovering from web-search issues.
- Partial completion details: After step 1, the agent had the user profile but no company context. After the failed search and first retry, it had partial research context but still needed a better Cedar Gate-specific result.
- Failure notes: The first web search used an invalid `topic` and failed validation. The subsequent search results were noisy and risked mixing Cedar Gate with unrelated Cedar/Cedars-Sinai results, so the run succeeded but exposed search-quality weakness.

## 2. profile_gap_study_plan

- Category: normal
- Goal: Exercise profile retrieval and synthesis with minimal tool usage.
- Expected behavior: Should use personal_profile_tool and finish without unnecessary retries.
- Actual behavior: The agent used `personal_profile_tool` once, identified the top three interview gaps from the profile, and returned a 7-day study plan plus a short Python practice question without any extra tool calls.
- Final status: `completed`
- Budget usage: 2 LLM calls, estimated cost `$0.002851`
- Replanning triggered: No.
- Partial completion details: None. The task was completed directly after the profile lookup.
- Failure notes: No runtime failures were observed in this run.

## 3. python_execution_demo

- Category: normal
- Goal: Exercise the code execution tool successfully.
- Expected behavior: Should call code_execution_tool with valid Python and finish cleanly.
- Actual behavior: The agent called `code_execution_tool` with valid Python, printed the first 8 Fibonacci numbers, and then explained the output in the final answer.
- Final status: `completed`
- Budget usage: 2 LLM calls, estimated cost `$0.001725`
- Replanning triggered: No.
- Partial completion details: After the tool call, the task was effectively solved and the final step only summarized the observed output.
- Failure notes: No runtime failures were observed in this run.

## 4. unsupported_language_trap

- Category: adversarial
- Goal: Test whether the agent avoids looping on an unsupported language request.
- Expected behavior: Should avoid repeated blind retries. A strong outcome is replanning or stopping with a clear explanation.
- Actual behavior: In this run, the planner did not invoke the code tool at all. It inferred directly that `console.log('hello from JS')` would print `hello from JS` and returned that as the final answer in one step.
- Final status: `completed`
- Budget usage: 1 LLM call, estimated cost `$0.000540`
- Replanning triggered: No.
- Partial completion details: None. The planner chose to answer immediately.
- Failure notes: This avoided looping, which is good for budget control, but it also means the run did not exercise the unsupported-language recovery path during this evaluation pass.

## 5. nonexistent_company_search_trap

- Category: adversarial
- Goal: Test whether the agent avoids overspending on an impossible or likely false search task.
- Expected behavior: Should stop cleanly or partially complete without exhausting the budget through repeated searches.
- Actual behavior: The agent performed one targeted news search, found no direct evidence for the fictional company, and then finalized with a clear statement that the claim was unsupported rather than wasting budget on repeated searches.
- Final status: `completed`
- Budget usage: 2 LLM calls, estimated cost `$0.003983`
- Replanning triggered: No.
- Partial completion details: The task was only partially satisfiable because the requested evidence did not exist. The agent verified absence of support and reported that instead of producing fabricated sources.
- Failure notes: The returned search results were unrelated or only loosely related to lunar/AI/mining topics, which reinforced that the company likely does not exist.
