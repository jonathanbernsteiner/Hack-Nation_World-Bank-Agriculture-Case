---
name: create-project
description: 'Turn a project idea, specification, transcript, or existing roadmap into a right-sized GitHub issue tree with single-purpose executable leaves, ready for Init. Use when planning or creating project epics, parent issues, dependencies, and leaves; not for generic repository scaffolding or implementing the issues.'
---

# Create Project

Turn the user's project into the smallest useful GitHub issue tree. GitHub is the durable engineering record: the tree should let a new agent understand the goal, prior decisions, dependencies, and next work without relying on another session's memory.

This skill designs and, when authorized, creates the project structure. It does not implement the resulting issues. Hand execution to `$init` after the tree is ready.

## Core rule: earn every layer

Do not add hierarchy merely because a project can be decomposed.

- Start with the flattest structure that can represent the work clearly.
- A single focused issue is valid for a single focused deliverable.
- A small project may need only a root with a few leaves, or no separate root at all when one issue fully captures the work.
- Add a parent only when it manages at least two meaningful children, carries shared decisions, clarifies ordering or dependencies, or creates a useful coordination boundary.
- Collapse a parent with one child unless there is a concrete reason to retain it.
- Never target a fixed depth, number of epics, number of children, or amount of work per layer.
- Do not split tiny work just to make the tree look complete.
- When the work is genuinely intricate, recurse as deeply as needed. Four to six levels can be appropriate, but depth is an outcome of complexity, never a goal.

Prefer the least structure that preserves agent comprehension, reviewability, and safe execution.

## Organize for top-to-bottom execution

Make the tree an explicit route that a fresh agent can follow from the root without reconstructing the plan.

- Group work by meaningful epics and features, adding intermediate parents only when they earn their layer. Keep each issue under the outcome it belongs to; shared prerequisites belong under a suitable shared parent and are linked from their consumers.
- List each parent's direct children in intended execution order, with prerequisites first where the grouping permits. The parent coordination board or ordered child list is the canonical order; keep native sub-issue order and the GitHub Project view consistent where supported. Issue numbers and creation dates do not determine execution order.
- Describe the traversal at the root: start at the top, recursively descend into each parent in listed order, and select the first ready executable leaf. Parents coordinate work and are never implementation tasks themselves.
- Skip completed work. When a leaf is blocked, continue to the next ready leaf in the same traversal; when a branch has no ready leaves, continue to the next branch. After a leaf completes, refresh statuses and blockers and scan from the root again so earlier work that has become ready is revisited. If unfinished work remains but no leaf is ready, report the blockers.
- Keep cross-feature work in its proper branch and record actual prerequisites as `Blocked by #123 — [required result and why]`. Use real issue links in live issues, including `owner/repo#123` or a full URL across repositories. Replace temporary draft identifiers after creation. An issue's location or preferred priority alone does not make it blocked.
- Record each blocker on the affected leaf and summarize dependencies across branches on their nearest shared parent. A blocker on a parent applies to all descendants only when the whole branch truly depends on it; otherwise mark only the affected leaves.
- Treat explicit dependencies as authoritative even when they require visiting a later branch first. List position expresses preferred order, not an implicit dependency. Any parallel starting set must still satisfy the parallel-work rules below.

Include this traversal rule in the root issue so execution agents can discover it without loading this skill. It defines how to select work; execution remains subject to the user's authorization and Init's workflow.

## One issue, one purpose

Every issue must have one clearly stated purpose. A parent may coordinate several children, but those children must all contribute to the parent's single shared outcome. Parents organize work; executable leaves perform it.

Every executable leaf must handle exactly one thing:

- One implementation outcome, or
- One bug fix, or
- One concrete decision or discovery artifact that unblocks implementation.

Never bundle two or three independently useful changes into one leaf. If the title or outcome naturally reads as "do X and do Y," split it unless Y is strictly necessary to complete X and has no independent value.

Required tests, small documentation updates, migrations, configuration, and cleanup may stay in the same leaf only when they directly implement or prove that one change. They are part of the definition of done, not additional outcomes. Multiple acceptance checks are also fine when they verify the same thing.

Use this independence test: if one part could be implemented, reviewed, merged, reverted, or handed to another agent without the other part, they are separate leaves.

Do not mechanically split one coherent behavior by file or technical layer. An endpoint's contract, implementation, and focused tests can remain one leaf when together they deliver one endpoint. Split them only when a prerequisite must settle first, the parts are independently deliverable, or the combined context is too large for one focused agent session.

## Source of truth and scope

- Resolve the repository, project goal, and available source material from the request and active context before asking for information.
- For an existing repository, inspect relevant code, repository instructions, documentation, open issues, linked pull requests, and the live GitHub Project when present.
- Treat live GitHub as authoritative for existing issues and project state. Local notes, transcripts, plans, and handoffs are inputs, not substitutes for current GitHub state. Newly agreed decisions in chat must be synchronized to GitHub so its record stays current.
- Reuse or reshape suitable existing issues instead of creating duplicates.
- Preserve the user's stated scope. Record attractive but unrequested ideas as exclusions or optional follow-ups rather than silently adding them.
- Do not create a repository, write implementation code, dispatch implementers, schedule heartbeats, or start `$init` work unless separately requested and authorized.

## Planning versus creation

Requests to plan, propose, preview, or explain are read-only unless the user has also authorized GitHub updates. Produce the draft tree in chat and retain agreed decisions with it for synchronization when creation is authorized.

Before creating or materially restructuring live GitHub issues, show the proposed tree, its important dependencies, and its first ready leaves. Wait for the user's approval unless the user has already explicitly approved that exact tree and target repository. Approval to create the tree is not approval to implement its leaves.

If live GitHub cannot be reached or authenticated, stop at a clearly labeled draft. Do not infer current state from a snapshot and create around it later without refreshing.

## Keep agreed chat decisions on GitHub

GitHub must contain enough context to continue without this chat. During project planning and follow-up discussion, capture every settled architectural decision, requirement, specification, clarification, constraint, scope addition or reduction, exclusion, and change to acceptance criteria or dependencies. Include relevant agreements from earlier in the available conversation, not only the latest message. Distinguish explicit user decisions and accepted proposals from suggestions, unanswered questions, and agent assumptions; do not present tentative ideas as settled.

For an established target repository and issues, this workflow authorizes posting agreed project decisions and updating the affected issue definitions without asking for separate permission to document each agreement. Respect an explicit draft-only or no-GitHub-write instruction. Creating new issues or materially restructuring the tree still follows the approval rule above; approval of the exact change already given in chat counts and must not be requested again.

After each batch of agreed decisions, before dependent work or a final handoff:

1. Review the available conversation for agreements not yet recorded. Refresh the relevant issue bodies and comments; reuse existing records and avoid duplicate comments.
2. Post a concise decision comment on the most specific relevant issue. Record what was agreed, the rationale actually discussed, what it changes or supersedes, and affected issue links. Do not invent reasons or paste the whole transcript. Use the decision format in [references/issue-formats.md](references/issue-formats.md).
3. Update the issue body wherever the agreement changes the current specification: outcome, scope, non-goals, constraints, acceptance criteria, validation, or dependencies. Comments preserve the history; the body must describe the current agreed work. Preserve unrelated contributions. When replacing an earlier decision, explicitly link or identify the superseded decision instead of silently erasing its history.
4. Put project-wide decisions on the root. For decisions affecting siblings or branches, summarize and link the canonical decision comment on the nearest shared parent, and update affected leaves so an agent entering through any of them sees the applicable constraints. Refresh ordering, blockers, and next ready work when affected.
5. Re-read the updated issues and comments to verify the agreements were saved and the bodies agree with them. Report the relevant GitHub links and any unsynchronized items; do not claim the context is recorded until verified.

If issues do not exist yet, keep the agreements attached to the draft and carry them into the approved creation pass: current definitions belong in bodies, with decision comments for their rationale and change history. If access fails, the target is ambiguous, or writes are explicitly deferred, retain an exact pending-sync list with intended destinations and explain the blocker. Refresh GitHub before retrying; a local note is not a completed sync. Do not hand off dependent execution as ready while a required decision exists only in chat.

## Build the tree

1. Establish the project outcome, completion criteria, constraints, non-goals, target repository, and any required human actions or access.
2. Inspect enough of the current system to distinguish new work from existing behavior and avoid speculative tasks.
3. Sketch the work flat first as concrete deliverables.
4. Group deliverables by epic or feature where a parent adds coordination value, and order each parent's children for top-to-bottom recursive traversal.
5. Recursively examine each proposed executable issue. Split any issue containing more than one implementation, fix, or independently useful outcome, then apply the remaining decomposition signals below.
6. Record ordering, `blocked by`, `unlocks`, external blockers, and work that can proceed independently.
7. Check the complete tree against the quality gate below.
8. Present the draft for approval or, when already authorized, create it in GitHub, synchronize agreed chat decisions, and verify the resulting relationships and decision records.

Use temporary plan identifiers while drafting when helpful, but follow the repository's naming conventions in live issue titles. Do not impose `Epic 01` numbering when the repository does not use it.

## Decomposition signals

Split an issue when doing so creates a real execution or review boundary, for example:

- It contains more than one implementation, bug fix, or independently valuable outcome.
- Its title or outcome joins separate actions with "and," "plus," or an equivalent list.
- It would reasonably require multiple focused pull requests.
- It combines unrelated decisions, systems, or validation strategies.
- One part can proceed while another is blocked.
- Separate owners or worktrees could execute parts without editing the same area.
- The context needed to investigate, implement, debug, and validate it is likely to exhaust one productive agent session.
- A prerequisite such as a schema, migration, contract, or interface must settle before dependent work can be specified safely.

Plan every implementation leaf and its corresponding PR tightly enough to confidently expect completion within 400 changed lines (additions plus deletions), including required tests, documentation, migrations, and configuration. Ground that estimate in the inspected code and a concrete approach; do not assert confidence without evidence. Record a brief estimate and its basis in the leaf.

If that confidence is missing, investigate enough to resolve the uncertainty, narrow the outcome, or split it at meaningful implementation or review boundaries before treating the leaf as ready. Do not split mechanically by file or technical layer, omit necessary tests, or compress code to fit the estimate. Parents coordinate larger outcomes and are not subject to this per-PR target; non-code leaves need one focused, verifiable deliverable.

The 400-line target guides project planning, not an implementation stop rule. If the actual diff grows during execution, reassess scope and reviewability; crossing the estimate alone does not require abandoning the issue or automatically splitting the PR.

For implementation work, require one focused, reviewable PR per leaf unless the repository workflow makes a PR inapplicable. A non-code leaf should still produce one clear, verifiable deliverable. If a leaf needs multiple PRs, split it; do not keep multiple implementation units together for convenience.

## Information carried by the tree

Every parent is a task manager for its direct children. It should explain the shared outcome, summarize each child in one or two useful sentences, show ordering and dependencies, surface shared decisions, and identify the next ready work.

Every executable leaf should be understandable without hidden session context. It should state its one concrete outcome, relevant boundaries and constraints, dependencies, acceptance criteria, and validation. Include likely code areas or interfaces only when supported by inspection; do not fabricate implementation details to make an issue look complete.

When a decision affects siblings, place the detailed reasoning on the issue where it arose and summarize it on the nearest shared parent. The parent should be sufficient for discovery; agents can drill into the leaf for evidence.

Use the formats in [references/issue-formats.md](references/issue-formats.md) when drafting or creating issues. Omit empty sections and keep simple issues simple.

## Parallel work

- Mark leaves parallel only when their dependencies are satisfied and their likely code ownership does not substantially overlap.
- Record required sequencing as explicit dependencies; the listed traversal order alone never makes an issue ready or blocked.
- Do not schedule blocked work merely because it could wait on a heartbeat. Record the dependency and readiness state; scheduling requires a separate request.
- Identify a small set of genuinely ready starting leaves. Do not label every unblocked idea as an immediate priority.

## Quality gate

Before presenting or creating the tree, verify:

- Every issue traces to the project outcome.
- Every parent adds actual coordination value.
- Every parent is completed by the combined outcomes of its children; missing work is visible.
- Every issue has one purpose, and every executable leaf contains exactly one implementation, fix, or concrete unblocking artifact.
- No leaf bundles independently mergeable work; supporting tests and edits only serve its one outcome.
- Every ready implementation leaf has an evidence-backed estimate supporting confident completion in one PR within 400 changed lines, including supporting tests and edits. Uncertain or larger work has been investigated, narrowed, or meaningfully decomposed.
- Dependencies are explicit, directional, and free of cycles.
- Walking the tree from the root in listed order, recursively skipping completed or blocked work, identifies the stated first ready leaf. Check that completing its prerequisites would make earlier blocked work discoverable on the next scan.
- Every issue belongs to the appropriate epic or feature; dependencies across branches have explicit issue links and a reason on the affected leaves and are summarized on the nearest shared parent.
- Existing issues are reused where appropriate and no planned leaf duplicates active work.
- Every settled agreement in the available conversation is represented in the draft or verified on GitHub, with current issue definitions and discoverable decision history. Pending synchronization is explicit.
- Human access, product decisions, and external approvals are visible as blockers rather than buried inside implementation issues.
- The tree is neither flatter than the complexity requires nor deeper than the work justifies.
- A fresh agent could enter through a leaf, read its ancestors and relevant siblings, and know what to do and why.

If the tree fails because a requirement or decision is genuinely unknown, create a focused discovery or decision leaf only when it has a concrete output that unblocks later work. Do not use vague research issues as placeholders.

## Create and verify in GitHub

After approval:

1. Refresh the repository, issue, and GitHub Project state immediately before writing.
2. Create or update parents and leaves without overwriting unrelated contributions.
3. Establish native parent/sub-issue relationships where available; otherwise use the repository's existing linking convention.
4. Add dependency relationships or explicit dependency sections consistently.
5. Populate each parent coordination board with its direct children in execution order, current status, blockers, and next ready work. Include the traversal rule at the root and align native ordering and the GitHub Project view where supported.
6. Synchronize all agreed chat decisions using the workflow above, including agreements made before the issues existed.
7. Re-read the created objects and verify titles, bodies, decision comments, links, hierarchy, traversal order, and dependency direction. Confirm all draft dependency identifiers resolve to real issues and no settled agreement remains only in chat.
8. Report the root issue, created or reused issues, important dependencies, decision links, unresolved human actions or pending synchronization, and first ready leaves.

Avoid noisy creation comments. Put stable project definition in issue bodies and reserve comments for chronological decisions and changes.

## Handoff to Init

Finish with a clean execution boundary:

- Name the first ready leaf or small set of independent ready leaves.
- Explain briefly why each is ready and what it unlocks.
- Link the recorded decisions and confirm the affected issue bodies reflect them. Carry forward any pending-sync items as explicit handoff blockers rather than relying on chat memory.
- State that project-tree approval did not authorize implementation unless the user explicitly granted that authority.
- Direct the next execution session to use `$init` on the chosen leaf. Init owns per-issue approval, worktree isolation, implementation, review, merge, decision propagation, and handoff updates.
