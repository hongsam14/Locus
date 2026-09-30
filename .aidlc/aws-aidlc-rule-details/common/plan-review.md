# Plan Review — Independent Review Before Approval Gates

**Purpose**: Before a stage's plan or design artifact is presented to the human for approval, an
independent reviewer sub-agent reads it with fresh eyes, writes a review record, and its findings
are shown to the human verbatim at the approval gate. The human always keeps the final say; the
review is decision support, never a hidden gate.

**Why**: The session that wrote an artifact is the worst judge of it. A second reader with no
access to the builder's reasoning catches broken cross-references, unstated assumptions, untestable
criteria, steps that contradict approved design decisions, and plans a developer could not execute
without guessing.

Load this file when entering a reviewed stage (see the table below). It is not loaded at workflow
start.

---

## 1. Which stages are reviewed

| Stage (moment) | Reviewed artifact (`review_artifact`) | Also passed as produced | Reviewer | Class | Review record |
|---|---|---|---|---|---|
| Requirements Analysis (after Step 7, before the approval prompt) | `aidlc-docs/inception/requirements/[<cycle>-]requirements.md` | verification / clarification question files | product-lead-reviewer | advisory | `aidlc-docs/inception/requirements/reviews/<stem>-review-NN.md` |
| User Stories — Part 2 (after generation, before the approval prompt) | `aidlc-docs/inception/user-stories/stories.md` | `personas.md`, the approved story plan | product-lead-reviewer | advisory | `aidlc-docs/inception/user-stories/reviews/stories-review-NN.md` |
| Application Design — Part 2 (after artifacts, before the approval prompt) | `aidlc-docs/inception/application-design/[<cycle>/]application-design.md` | `components.md`, `component-methods.md`, `services.md`, `component-dependency.md`, the approved design plan | architecture-reviewer | advisory | `aidlc-docs/inception/application-design/[<cycle>/]reviews/application-design-review-NN.md` |
| Units Generation — Part 2 (after artifacts, before the approval prompt) | `.../application-design/[<cycle>/]unit-of-work.md` | `unit-of-work-dependency.md`, `unit-of-work-story-map.md`, the approved unit plan | architecture-reviewer | advisory | `.../application-design/[<cycle>/]reviews/unit-of-work-review-NN.md` |
| Functional Design (per unit, after Step 6) | `aidlc-docs/construction/{unit}/functional-design/business-logic-model.md` | `business-rules.md`, `domain-entities.md`, `frontend-components.md` (if any), the FD plan | architecture-reviewer | adversarial (max 2) | `aidlc-docs/construction/{unit}/functional-design/reviews/functional-design-review-NN.md` |
| NFR Requirements (per unit, after Step 6) | `.../{unit}/nfr-requirements/nfr-requirements.md` | `tech-stack-decisions.md` | architecture-reviewer | adversarial (max 2) | `.../{unit}/nfr-requirements/reviews/nfr-requirements-review-NN.md` |
| NFR Design (per unit, after Step 6) | `.../{unit}/nfr-design/nfr-design-patterns.md` | `logical-components.md` | architecture-reviewer | adversarial (max 2) | `.../{unit}/nfr-design/reviews/nfr-design-review-NN.md` |
| Infrastructure Design (per unit, after Step 6) | `.../{unit}/infrastructure-design/infrastructure-design.md` | `deployment-architecture.md`, `shared-infrastructure.md` | architecture-reviewer | adversarial (max 2) | `.../{unit}/infrastructure-design/reviews/infrastructure-design-review-NN.md` |
| Code Generation — Part 1 (per unit, after Step 5 plan summary, before Step 6 approval prompt) | `aidlc-docs/construction/plans/{unit}-code-generation-plan.md` | (none) | architecture-reviewer | adversarial (max 2) | `aidlc-docs/construction/plans/reviews/{unit}-code-generation-plan-review-NN.md` |

**Not reviewed by this rule** (same as the source framework): Workspace Detection, Reverse
Engineering, Workflow Planning (execution plan), Part 1 question plans (the `[Answer]:` plans — the
human answers those directly), Code Generation Part 2 generated code (use `/code-review` on the
diff as before), Build and Test, Operations.

**Light stages**: when a per-unit design stage runs at Minimal depth and produces a single light
note (e.g. `nfr/nfr-light.md`), lower the class to `advisory` and key the review record to that
note.

**Per-cycle overrides**: the human may lower or disable the class for a cycle or a stage ("이번
사이클은 advisory로", "U1 플랜은 리뷰 없이"). Record it in `aidlc-docs/aidlc-state.md` under
`## Plan Review Configuration` (stage · class · decided at) and log it in `audit.md`. Overrides
only lower the class (`adversarial` → `advisory` → `none`); the table above is the default when no
configuration exists. Never lower the class on your own initiative.

**Reviewer personas** live in `common/reviewers/`:

- `common/reviewers/architecture-reviewer.md` — design soundness, cross-references, implementability, plan executability
- `common/reviewers/product-lead-reviewer.md` — completeness, testability, traceability, scope

---

## 2. Review classes

- **`advisory`** — ONE review pass as decision support for the human gate. Whatever the verdict, do
  NOT re-edit the artifact and do NOT re-run the reviewer during normal flow: record the verdict,
  then present the gate with the findings quoted verbatim for the human to triage. Default for
  INCEPTION prose stages, where readiness is a judgment call that belongs to the human.
- **`adversarial`** — a refute-and-repair loop: up to `max_iterations` (default 2) reviewer passes
  with builder fixes between them, then the gate. Default for CONSTRUCTION stages, where findings
  are checkable and fix loops converge.

---

## 3. Flow

### 3.1 Request the review

1. Prerequisites: every artifact the stage produces exists, all `[Answer]:` tags of this stage are
   answered and analyzed (no open ambiguity), and the artifact is in the state you would present to
   the human. Do not request a review of a draft you still intend to edit.
2. Determine `iteration` (1 for the first pass of this attempt; +1 per re-dispatch) and the
   review record path from the table (`NN` = zero-padded iteration; a Request-Changes revision
   continues the numbering, it does not restart it).
3. Log the request in `aidlc-docs/audit.md` (append only):

```markdown
## Plan Review Requested — [Stage Name][ — unit]
**Timestamp**: [ISO timestamp]
**User Input**: (none — automatic per plan-review.md)
**AI Response**: Dispatching [reviewer] (class [advisory|adversarial], iteration [n]) on `[review_artifact]`. Review record: `[path]`.
**Context**: [Stage] — review requested before approval gate.

---
```

4. Narrate one sentence, in the conversation's language (see § 6), then dispatch.

### 3.2 Dispatch the reviewer sub-agent

Invoke the reviewer as a **separate sub-agent** and wait for it to finish (foreground). Do not edit
the reviewed artifact while it runs.

- **Claude Code**: use the `Agent` tool with `subagent_type` = `aidlc-architecture-reviewer` or
  `aidlc-product-lead-reviewer` (project agents under `.claude/agents/`; they load the persona
  from `common/reviewers/`). Claude Code loads `.claude/agents/` at session start, so after adding
  or editing them restart the session. If the agent type is not available (not yet loaded, or
  another harness), dispatch a general-purpose sub-agent (`model: sonnet`) whose prompt first
  orders the persona preflight — read the persona file and adopt it, use no Write/Edit tool,
  write the record by shell heredoc only — followed by the dispatch brief below.
- **Other harnesses**: use the harness's sub-agent facility with the persona file content as the
  agent's instructions.

**Dispatch brief** — pass, as paths (the reviewer reads them itself):

- Stage rule file: the `inception/<stage>.md` or `construction/<stage>.md` file this stage follows
  (so the reviewer knows what SHOULD have been produced)
- The stage's Q&A / plan file(s) with the human's `[Answer]:` values (context and constraints)
- `review_artifact` and every other artifact this stage produced (from the table)
- Consumed upstream artifacts — paths only, so claims can be verified against what they formalize:
  - Requirements Analysis: reverse-engineering artifacts (brownfield)
  - User Stories: `requirements.md`
  - Application Design: `requirements.md`, `stories.md`, RE `architecture.md` / `code-structure.md` (brownfield)
  - Units Generation: application-design artifacts, `requirements.md`, `stories.md`
  - Functional Design: this unit's `unit-of-work.md` entry, `unit-of-work-story-map.md`, `requirements.md`, `components.md`, `component-methods.md`
  - NFR Requirements / NFR Design / Infrastructure Design: this unit's functional-design artifacts, `unit-of-work.md`, `requirements.md`
  - Code Generation plan: this unit's design artifacts (FD / NFR / Infra, if produced), `unit-of-work.md`, application-design artifacts, `requirements.md`, RE `code-structure.md` (brownfield), plus read-only access to the workspace source the plan names
- The review record path — the ONE file the reviewer writes
- `class` (advisory | adversarial), `iteration`, `max_iterations`
- On every re-dispatch: `Prior findings (carry IDs forward):` followed by the previous review
  record's findings table with human dispositions overlaid (§ 3.6). The reviewer preserves those
  IDs and updates their statuses; it never renumbers.
- **Review-content boundary**: do not raise a finding whose sole subject is this stage's own
  review bookkeeping (iteration counters, review state, a review path). Judge the product claims.
- **Read scope** (per-unit stages): this unit's artifacts plus the passed upstream paths. Do NOT read
  other units' `aidlc-docs/construction/<other-unit>/` content by any means (file reads, grep, or
  glob spanning sibling unit paths), except to spot-check one integration point this unit's design
  explicitly names — and only the owning file, resolved via the shared inception artifacts.
- **Checks the reviewer may run** (read-only shell): path existence for every file a plan names
  (`ls`, `git ls-files`), symbol / call-site search for every rename a plan lists (`grep -rn`),
  Mermaid syntax sanity per `common/content-validation.md`, ID resolution (FR-x, US-x, BR-x,
  component names) against the passed upstream artifacts. Never run anything that writes,
  installs, or mutates the workspace.
- **Output contract**: the reviewer writes exactly one file (the review record, § 4), writes nothing
  else, and its return message's FIRST line is `**Reviewer:** <reviewer-name>` followed by the
  verdict and findings.

Do NOT pass: `aidlc-docs/audit.md`, `aidlc-docs/aidlc-state.md`, or any of your own reasoning
about the artifact. The reviewer forms independent judgment.

### 3.3 Read the verdict

After the sub-agent returns, open the review record and check that it is complete: the file
exists, opens with `## Review`, carries exactly one `**Verdict:** READY` or `**Verdict:** NOT-READY`
line, one `**Reviewer:**` line, one `**Iteration:**` line, and a `### Findings` table in the
template's column order (an empty table is valid). Anything else is an **incomplete attempt**, not a
verdict:

- **First incomplete attempt**: re-dispatch exactly once with the same iteration number and the
  same brief; note `Retry: incomplete review` in the audit request entry.
- **Second incomplete attempt**: stop retrying. Write a fallback review record at the same path
  with `**Verdict:** NOT-READY` and a single finding
  `R-01 | Major | <review_artifact> > review completion | review did not complete within its turn budget | Request changes and rerun the reviewer. | Unresolved`,
  and proceed as that NOT-READY directs for the class (advisory: gate; adversarial with iterations
  remaining: skip the fix and go straight to a fresh iteration — the artifact itself was never
  reviewed, so there is nothing to act on; adversarial exhausted: gate).

Log the verdict in `aidlc-docs/audit.md`:

```markdown
## Plan Review Completed — [Stage Name][ — unit]
**Timestamp**: [ISO timestamp]
**User Input**: (none)
**AI Response**: [reviewer] iteration [n] → **[READY|NOT-READY]**. Findings: [c] Critical / [m] Major / [k] Minor; open [o]. Record: `[path]`.
**Context**: [Stage] — [next: approval gate | builder fix + re-review | fresh iteration].

---
```

Update the stage's progress line in `aidlc-docs/aidlc-state.md` with
`review: [reviewer] iter [n] [READY|NOT-READY] (open [o])`.

### 3.4 Branch on class and verdict

**`advisory`** — both verdicts are terminal. Go to the gate (§ 5). The human triages; a Request
Changes at the gate is how an advisory finding becomes a revision.

**`adversarial`**:

- **READY** → terminal. Go to the gate.
- **NOT-READY** and `iteration < max_iterations` → say the fix line (§ 6), then fix the artifact
  yourself (you are the builder — no sub-agent), addressing each open finding at its `Location`
  with its `Required action`. Fix ONLY this stage's artifacts. Then return to § 3.1 step 2 with
  `iteration + 1`, passing prior findings.
- **NOT-READY** and iterations exhausted → say the exhausted line (§ 6), then go to the gate with
  the unresolved findings.

**A finding that requires changing an approved upstream artifact** (an earlier stage's approved
design, requirements, or plan) is NOT fixed in the loop. Leave it open with a note
`requires upstream change: <artifact>`; it goes to the human at the gate, who chooses between
accepted risk, a scoped change, or reopening the earlier stage (see the global 메타인지 rule: no
silent backward jump to satisfy a rule).

### 3.5 Freeze after the terminal verdict

Between the terminal verdict and the human's gate answer, do not edit the reviewed artifact or any
other artifact of this stage. Suggestions riding along a READY verdict are gate input for the human,
not defects: quote them at the gate, do not apply them.

If you nevertheless must edit a reviewed artifact before the human answers (you found an error
yourself), the verdict is **stale**: request exactly one recovery review (next iteration, same
brief, `Why now: Re-check after the artifact changed`), record its verdict as terminal, then stop
editing and present the gate. If the artifact changes again after that recovery verdict, request no
further review: present the gate with a `**Reviewed content differs:**` line naming the changed
paths, and let the human decide.

### 3.6 Human dispositions and the revision path

Dispositions are audit data, never artifact edits:

- **Approve** at the gate → every finding still `New` or `Unresolved` becomes `Accepted risk`.
  Log them in `audit.md` (`## Plan Review Dispositions — [Stage]`, one line per finding
  `R-NN → Accepted risk`). They are carried into any later re-dispatch's prior-findings table.
- **Request Changes** → open findings stay open. When the human explicitly says a finding does not
  apply ("R-02는 해당 없음: <이유>"), log `R-02 → Rejected: <exact human reason>`. Never infer a
  rejection from generic revision feedback.
- **Revision path**: after Request Changes, revise the artifact, then re-run this review before
  re-presenting the gate — `adversarial` re-enters with a fresh iteration budget, `advisory` runs one
  fresh pass — with prior findings passed (statuses updated by the reviewer, dispositions overlaid by
  you). Re-present the gate with `Why now: Revision re-checked.` Never re-present a reviewed stage's
  gate on a verdict that predates the revision.

### 3.7 Session continuity

On resume (`session-continuity.md`), if `audit.md` shows a `Plan Review Requested` entry for the
current stage without a matching `Plan Review Completed`, treat it as an incomplete attempt
(§ 3.3) and re-dispatch. If a verdict exists but the artifact was edited after it (compare the
record's date with the file's modification time when in doubt), treat the verdict as stale (§ 3.5).

---

## 4. Review record format

The reviewer writes exactly this shape, and nothing else, to the review record path. Only one H2
(`## Review`); everything below it is H3 or deeper. Findings are written in the language of the
reviewed artifact; the `ID`, `Severity`, and `Status` tokens stay in English verbatim.

```markdown
## Review

**Verdict:** READY | NOT-READY
**Reviewer:** architecture-reviewer | product-lead-reviewer
**Stage:** [Stage Name][ — unit]
**Reviewed artifact:** `[review_artifact path]`
**Class:** advisory | adversarial
**Iteration:** [n]
**Date:** [UTC ISO timestamp from `date -u +"%Y-%m-%dT%H:%M:%SZ"`]

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Critical | aidlc-docs/construction/plans/U1-...-plan.md > Step 5.2 | ... | ... | New |
| R-02 | Major | ... | ... | ... | New |
| R-03 | Minor | ... | ... | ... | New |

### Checks Run

| Check | Result | Interpretation |
|---|---|---|
| paths named in Steps 2–5 exist | 41/43 exist; 2 declared new | OK |
| grep call sites of `is_rumor` | 7 hits, plan lists 5 | Confirms R-02 |

### Summary

[1–2 sentences: the main concern, or why it is ready.]
```

- `ID` values are stable (`R-01`, `R-02`, …): never renumber, reuse, or drop an ID across
  iterations. New findings take the next unused ID and status `New`.
- `Location` is a workspace-relative artifact path followed by ` > ` and the exact section, step,
  or element.
- `Required action` states the concrete work in plain language. The reviewer does not rewrite the
  artifact.
- `Status` is exactly one of `New`, `Unresolved`, `Resolved`, `Rejected: <reason>`,
  `Accepted risk`. On a re-dispatch the reviewer reproduces every prior row, re-checks its location,
  and sets the status; a partial fix stays `Unresolved` with `Required action` narrowed to what
  remains. `Rejected` and `Accepted risk` are preserved only when the prior-findings input carries
  them — the reviewer never invents a disposition.

**Severity and verdict rules** (both reviewers):

| Severity | Meaning | Blocks READY? |
|---|---|---|
| Critical | Cannot be implemented / executed from this; fundamental gap or contradiction | Yes |
| Major | Implementable but will cause rework, confusion, or a contradicted approved decision | Yes, if more than 2 |
| Minor | Improvement opportunity | No |

- **READY**: zero Critical, at most 2 Major, any number of Minor
- **NOT-READY**: any Critical, or more than 2 Major
- Count only findings whose `Status` is `New` or `Unresolved`. Rows marked `Resolved`, `Rejected`, or
  `Accepted risk` do not weigh on the verdict.
- A finding backed only by taste is a suggestion (write it under `### Summary`), not grounds for
  NOT-READY. Every finding names checkable evidence: an ID that does not resolve, a path that does
  not exist, a criterion QA could not test, a step that contradicts a passed upstream artifact.

**Review bookkeeping is not artifact content.** Never copy the review's verdict, iteration, finding
statuses, or record path into the reviewed artifact or any other stage artifact — not as a header,
a table, or a section. The review record and `audit.md` hold it. (An artifact's own lifecycle
status, such as an ADR's `Status: Accepted`, is content and stays.)

---

## 5. Gate presentation — the Review brief

At every reviewer-backed approval gate, print the Review brief immediately BEFORE the stage's
standard `📋 REVIEW REQUIRED` / `🚀 WHAT'S NEXT?` block, after the completion announcement and the
AI summary. Keep the stage's standard option set and order unchanged; a riding suggestion never
makes "Request Changes" the recommended option. The global question rules still apply on top (the
two 원하시는 것 / 지금 하는 것 lines first, consequences per option).

```markdown
**Stage:** [Stage Name][ — unit]
**Review outcome:** [Concerns remain for your decision. | No open findings remain. | No blocking concerns were found. | The review did not complete with actionable findings.]
**Why now:** [First review completed. | Revision re-checked. | Re-check after the artifact changed.]
**Reviewed artifact:** `[review_artifact]`
**Review record:** `[review record path]` (iteration [n], [reviewer])
[**Reviewed content differs:** `[changed paths]` — only when § 3.5's second-change case applies]

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
[every finding whose status is New or Unresolved, verbatim from the record; omit the table when there are none]

[Suggestions the reviewer offered under Summary, quoted verbatim, if any]

**Decision options:**
- **Approve** — continue with the open findings accepted; they are recorded as `Accepted risk` and carried forward.
- **Request Changes** — return to the artifact so the required actions can be addressed; the review runs again on the revision. Name any finding you reject as inapplicable, with the reason.
```

Outcome wording: `Concerns remain for your decision.` when any finding is open; `No open findings
remain.` when findings exist but all are resolved or dispositioned; `No blocking concerns were
found.` when the record has no findings; `The review did not complete with actionable findings.`
on the § 3.3 fallback. Do not print the raw verdict token as the headline; the table and outcome
say what matters.

---

## 6. What the user hears

Only these sentences are spoken about the review; everything else in this file is silent
bookkeeping. Say them in the conversation's language (Korean renderings given). Name the reviewer
by trade (설계 검토자 / 제품 검토자), never by file or slug. Do not narrate dispatching, sub-agents,
iterations, budgets, records, or a verdict token ("NOT-READY가 나왔습니다" is never said).

- Before the check — "Let me have the [architecture / product] reviewer check this over before you
  see it." — **"보여 드리기 전에 [설계 / 제품] 검토자에게 한 번 살펴보게 하겠습니다."**
- Findings came back and you are fixing them (adversarial, once per round) — "Fair points came
  back; let me tighten [the specific thing, in plain terms] and re-check." —
  **"타당한 지적이 돌아왔습니다. [무엇을]을 손보고 다시 검토받겠습니다."**
- Concerns remain after the last round — "I had this checked [N] times and [N] concern(s) are
  still open. They are in the review record and I will flag them at the decision below." —
  **"[N]번 검토받았는데 [N]건이 아직 열려 있습니다. 아래 결정에서 함께 보여 드리겠습니다."**
- A revision changed the work, so the check runs again — "Those changes are in. Let me get them
  checked over again before you look." — **"수정을 반영했습니다. 보시기 전에 다시 한 번 검토받겠습니다."**

When a stage has no reviewer (or the class is `none`), nothing is said about it.

---

## 7. What the reviewer does NOT do

- Does not modify the reviewed artifact, any other stage output, `audit.md`, `aidlc-state.md`, or
  application code — its only write is the review record
- Does not talk to the human; the orchestrator mediates everything
- Does not see the builder's reasoning, the audit log, or the state file
- Does not block the workflow — the human always gets the final say at the gate
- Does not run for stages absent from the table, or when the effective class is `none`
