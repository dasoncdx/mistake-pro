# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

## 5. Docs Must Stay In Sync With Code

**Every change to the application must be reflected in the three spec documents.**

Whenever you modify `app.py`/`run.py` or any runtime behavior:
1. **PRD.md** — update if the change adds, removes, or alters a feature described in the product requirements. Keep the functional checklist accurate.
2. **TECH_DESIGN.md** — update if the change affects architecture, data model, API design, tech stack, deployment config, or compliance/legal copy. The tech doc must always describe the system as it actually runs.
3. **DESIGN.md** — update if the change alters UI layout, navigation structure, color usage, typography, component spec, or page flow. The design doc describes what the user sees.

**Rule of thumb:** After any git commit that changes app behavior, ask: *"Which of the three docs would this commit make inaccurate?"* Then update those docs in the same commit — or immediately after.

**This project has four sources of truth, and they must agree:**
```
PRD.md = what we're building
TECH_DESIGN.md = how we built it
DESIGN.md = what it looks like
run.py (code) = what it actually does
```

## 6. Dependency & Environment Management

**Search before install. Ask before large downloads.**

Before installing any package, library, or tool:
1. **Search first** — check if it already exists on this machine:
   - Python packages: check across all installed Python versions (`python3.12 -c "import X"`, `python3.11`, etc.)
   - System tools: `which X`, `brew list X`, or check common paths
   - Look for venvs in the project directory that may already have dependencies
2. **Use what exists** — prefer the already-installed version over re-installing
3. **Large installs require confirmation** — if a download/install is estimated to take more than 30 seconds or exceeds 100MB, pause and ask the user:
   - State what needs to be installed, why, and estimated size/time
   - Offer to provide manual install commands the user can run themselves
   - Wait for explicit confirmation before proceeding

**Rationale:** Reinstalling existing packages wastes time and bandwidth. Large downloads may hit network constraints or user preferences the agent cannot anticipate. The user is the best judge of when and how to install heavyweight dependencies.
