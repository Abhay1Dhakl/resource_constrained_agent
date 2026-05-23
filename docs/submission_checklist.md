# Submission Checklist

## Hard constraints
- [ ] Agent enforces max 10 LLM calls per task
- [ ] Agent enforces max $0.20 per task
- [ ] If budget is hit, execution stops immediately
- [ ] If budget is hit mid-task, agent reports partial progress cleanly

## Core architecture
- [ ] Planning loop implemented
- [ ] Exactly 3 tools
- [ ] Tool 1: web search
- [ ] Tool 2: code execution
- [ ] Tool 3: custom tool
- [ ] Every tool has a timeout
- [ ] No `except: pass` anywhere
- [ ] After each tool call, agent checks progress
- [ ] If no progress, agent replans instead of retrying blindly
- [ ] At least one clear replanning trace exists

## Testing and evaluation
- [ ] 5 distinct tasks tested
- [ ] At least 2 adversarial tasks included
- [ ] Results documented for each task
- [ ] Partial completions documented
- [ ] Replanning triggers documented
- [ ] Failures documented

## Deliverables
- [ ] Dockerfile exists and works
- [ ] `.env.example` exists
- [ ] README has all required sections
- [ ] `decisions.md` exists
- [ ] Repo runs with a single command

## Current Status
- [x] ReAct-style planning loop scaffold exists
- [x] Exactly 3 tools are implemented and wired
- [x] Web search tool exists
- [x] Code execution tool exists
- [x] Custom tool exists
- [x] `.env.example` exists
- [x] No `except: pass` blocks found
- [ ] Budget stop behavior is clean and immediate in all cases
- [ ] Mid-task partial progress is reported correctly on budget stop
- [ ] Every tool has a timeout
- [ ] Reflection after each tool call is enforced in code
- [ ] Replanning is demonstrated with a clear successful trace
- [ ] README is complete
- [ ] Dockerfile is complete
- [ ] pyproject.toml is complete
- [ ] `decisions.md` exists
- [ ] `test_results.md` exists
- [ ] 5 evaluation tasks are documented
- [ ] 2 adversarial tasks are documented
- [ ] Project runs from a clean shell with a single command
