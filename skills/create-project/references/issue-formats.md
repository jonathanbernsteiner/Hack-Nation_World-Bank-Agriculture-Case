# Issue formats

Use these as adaptable content shapes, not mandatory boilerplate. Omit sections that add no information. A short leaf should remain short.

## Single-purpose check

Before using either leaf format, state the leaf's outcome in one sentence. It must describe exactly one implementation, one bug fix, or one concrete unblocking artifact.

Split the leaf when:

- The sentence contains separate actions joined by "and" or "plus."
- Either part could be merged, reverted, validated, or handed off independently.
- Completing one part would still leave a second independently meaningful task.

Do not count focused tests, required migrations, small documentation changes, or configuration needed for that same outcome as separate things. They belong in validation or scope for the one change.

Parent issues are not executable bundles. Each parent has one shared outcome and coordinates the single-purpose leaves beneath it.

## Root project or major parent

```markdown
## Outcome
[What will be true when this project is complete.]

## Completion criteria
- [Observable project-level result]

## Scope
[Important boundaries, constraints, and non-goals.]

## Coordination board
| Child | Purpose | Status | Blocked by | Output/PR |
|---|---|---|---|---|
| #123 | [One or two useful sentences] | Ready | — | — |

## Execution order
Read the coordination board top to bottom and recursively visit each parent's children in their listed order. Select the first ready executable leaf, skipping completed or blocked work and continuing to the next branch when needed. After completion, refresh statuses and dependencies and scan from the root again. Explicit blockers override list position. If unfinished work remains but nothing is ready, report the blockers.

## Ordering and dependencies
[Dependencies across branches, with issue links and the required result.]

## Shared decisions
- [Accepted decision and link to detailed evidence]

## Human actions
- [Access, approval, or decision and its owner]

## Next ready work
- #123 — [Why it is ready and what it unlocks]
```

For a small project, replace the table with a short task list if that is clearer. Do not add a coordination board to a one-issue project.

Put rows or list entries in intended execution order. Include the execution rule at the root; other parents can refer to it. Keep issues under their owning epic or feature even when their prerequisites live in another branch.

## Intermediate parent

```markdown
## Outcome
[The shared result delivered by these children.]

## Children in execution order
1. #123 — [Purpose and boundary; current status]
2. #124 — [Purpose and boundary; current status]

## Dependencies and order
- #124 is blocked by #123 because [reason].

## Completion criteria
- [Combined result of the children]

## Shared constraints or decisions
- [Only information that affects more than one child]

## Next ready work
- #123
```

An intermediate parent should usually have at least two meaningful children. If it merely renames its only child, collapse it.

## Executable leaf

```markdown
## Outcome
[Exactly one implementation, bug fix, or unblocking artifact.]

## Why
[Brief project context when the title and parent do not make it obvious.]

## Scope
- [Work strictly required for this one outcome]

## Out of scope
- [Only likely points of confusion]

## Dependencies
- Blocked by: #123 — [Required result and why; list every actual prerequisite, or state none. Name external decisions/access and their owner when applicable.]
- Unlocks: [issue or outcome, when useful]

## Acceptance criteria
- [Observable evidence that the one outcome works]
- [Relevant edge case for that same outcome]

## Validation
- [Targeted test, inspection, or review evidence]

## Size estimate
[Expected changed lines, including tests and supporting edits, and the inspected code/approach supporting confidence that this fits within 400 lines. Omit for non-code leaves.]

## Context
- Parent: #123
- Relevant decisions/interfaces: [links or inspected locations]
```

Do not guess file paths, APIs, or test commands. Include them only when repository inspection supports them.

## Compact leaf

Use this when the work is genuinely small:

```markdown
## Outcome
[Exactly one implementation, bug fix, or unblocking artifact.]

## Acceptance criteria
- [Observable result]

## Validation
- [Evidence required]

Size estimate: [Expected changed lines and brief basis for confidence this fits within 400 lines, including tests and supporting edits; omit for non-code leaves.]

Blocked by: #123 — [Required result and why, or none]
Parent: #123
```

## Draft tree presentation

Before live creation, show the user a compact tree plus the important execution facts:

```text
Project outcome
├── Feature A
│   ├── A1 [ready]
│   └── A2 [blocked by B1: needs shared contract]
└── Feature B
    ├── B1 [ready]
    └── B2 [blocked by A2: needs integration result]
```

Default traversal: A1, then B1 while A2 is blocked, then return to A2, then B2. A2 stays under Feature A because that is the outcome it serves. These are temporary draft identifiers; live issues must use real issue references. Nest under epics when the project needs that extra coordination layer.

Then list:

- Why each parent exists.
- The non-obvious dependencies.
- First ready leaves.
- Human blockers.
- Any implementation leaf whose size remains uncertain and the investigation or decomposition needed before it is ready.

Do not repeat every issue body in the approval message.

## Agreed decision or scope-change comment

Use one concise comment per coherent batch of agreements. Omit fields that add no information, but keep enough context for someone who never saw the chat.

```markdown
## Agreed decision — [short description]

- Decision: [What the user decided or accepted; include precise boundaries.]
- Reason: [Rationale discussed, when available.]
- Changes: [Effect on scope, architecture, specifications, acceptance criteria, or dependencies.]
- Supersedes: [Earlier decision/comment link and what changed, when applicable.]
- Affected issues: [Real issue links.]
```

After posting, update affected issue bodies to reflect the current agreement. Link the canonical comment from their context or shared-decisions sections and summarize it on the nearest shared parent when it affects multiple children. Preserve previous comments as history, and avoid reposting agreements already recorded accurately.
