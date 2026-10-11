# Reduce repeated context and development cost

Root `AGENTS.md` provides a compact starting context. Focused docs avoid loading the full beginner README on every coding task. They help only while accurate: source is authoritative; update the relevant doc when behavior changes.

## Task prompt template
```text
Goal: [one concrete behavior/change]
Acceptance: [what should work when finished]
Scope: [local/GCP, UI/API, constraints]
Start with AGENTS.md and docs/feature-map.md; read only relevant files.
Use the smallest meaningful existing checks. Report outcome and remaining issues.
```

## Practical habits
- Group related small edits in one request; avoid combining unrelated redesigns. Clear acceptance criteria reduce rework.
- Start a fresh chat for a new independent task when old conversation history is irrelevant. Point it to AGENTS.md and a current status file; a repository doc does not remove history already in an existing chat.
- Share the exact error plus a short relevant log excerpt rather than whole terminal history. Exclude secrets.
- Ask for a targeted code change or explanation; specify brevity if you do not need a tutorial. Save durable explanations in docs rather than repeat them in prompts.
- Use existing scripts for deterministic checks, and deploy only when needed. Do not create expensive cloud infrastructure to validate a local UI edit.
- For model selection, use your product's available cost/usage controls and a model appropriate to task complexity; this repository cannot set billing or model choice.

There is no guaranteed percentage saving. Token usage depends on tool output, conversation history, model and task. These files reduce unnecessary discovery and repeated explanations; they do not change provider pricing or impose spending caps.
