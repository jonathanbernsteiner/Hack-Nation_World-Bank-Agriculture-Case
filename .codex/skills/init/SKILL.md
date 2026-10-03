---
name: init
description: 'Initialize or resume GitHub issue-tree orchestration: use parent issues as task managers and shared discussion boards, record decisions on leaf and parent issues, and prepare agent handoffs. Use for this issue-based coordination workflow or $init; not generic repository or framework initialization.'
---

# Init — issue-tree orchestration

Use the GitHub issue tree as the operational record for the user's authorized work. Parent issues coordinate children and provide a shared board for people and agents to understand progress, decisions, and next actions.

## Scope

- Resolve the repository and assigned issue from the request or active task. Inspect available context before asking for a missing target.
- Treat the live GitHub repository and, when applicable, its live GitHub Project as the source of truth. Local checkouts, cached tool results, exports, handoffs, summaries, and conversation context are snapshots that may help locate work but must not be used as substitutes for current GitHub state.
- Invoking this skill for a specific issue authorizes routine coordination comments and board maintenance for that work. Requests to explain or preview the workflow remain read-only. Installation alone does not authorize repository changes.
- Follow repository instructions and applicable GitHub writing conventions.
- Context-sharing infrastructure, Obsidian synchronization, and copying knowledge bases are outside this skill. Link relevant existing context as needed.
- Recurring heartbeats and scope expansion require applicable authorization. Merges of approved issue work follow the main-agent merge authorization below. Record proposed follow-up work where appropriate.

## Main-agent role: orchestration only

The main agent receiving `$init` is the orchestrator. Research the problem, determine the approach, identify affected code, define implementation tasks and validation criteria, delegate changes to implementer agents, and review their results.

- Never write or modify implementation code yourself unless Ethan explicitly authorizes the main agent to do so. This includes tests, implementation configuration, small fixes, and code changes needed to resolve merge conflicts.
- Issue approval, autonomous continuation, recursive delegation, and permission to use subagents do not grant permission for the main agent to implement code.
- Send specific actionable findings back to the implementer, review the returned fixes, and repeat until resolved. Do not take over the edits yourself.
- Read-only investigation, running validation, maintaining issue/PR coordination records, and the Git operations authorized elsewhere in this skill remain main-agent responsibilities.
- Follow the existing subagent approval gate. If delegation is not authorized or available, continue read-only preparation and raise the blocker with Ethan; do not silently implement the changes yourself.

## Per-issue approval gate

Never start implementing an issue before Ethan approves that issue, unless he has explicitly granted autonomous issue-selection and implementation authority as described below. Always raise the specific issue with him first, explaining at a high level what you intend to implement, why it is needed, and how you plan to implement and validate it. Wait for his approval before claiming the issue, creating its implementation worktree, dispatching an implementer, or changing code. Read-only inspection to prepare this explanation is allowed.

Approval for one issue does not authorize the next issue. Existing explicit approval for that exact scope remains valid when resuming; a material scope change must be raised again. Invoking `$init`, a dependency becoming ready, or an agent choosing a next task is not issue approval.

Do not spawn subagents without asking Ethan first. An explicit instruction to work recursively authorizes subagent spawning within that requested work, including recursive delegation. It does not waive the per-issue approval gate unless Ethan also grants the explicit autonomous authority described below. Main-agent review remains required even in recursive mode.

### Autonomous continuation gate

- By default, finish or hand off the currently approved issue, identify the next live ready issue, explain the proposed work, and wait for Ethan's approval before starting it.
- Do not infer autonomous authority from `$init`, broad project context, a request to coordinate or plan the project, permission to use subagents, recursive delegation, approval of a parent issue, or phrases such as "keep going" when they do not clearly authorize selecting and implementing additional issues.
- Autonomous continuation is allowed only when Ethan explicitly says the agent may independently select and implement additional issues without asking for approval each time. Record that authorization and its repository, GitHub Project, issue set, time, risk, or other stated boundaries on the relevant parent issue or coordination board.
- Autonomous authority waives the per-issue approval wait only within those explicit boundaries. It does not authorize material scope expansion, unrelated repositories or projects, destructive operations, production deployment or provisioning, bypassing required reviews or checks, or actions otherwise requiring separate authorization.
- If the wording or boundary of autonomous authority is unclear, do not start another issue. Present the next candidate and wait for Ethan's explicit approval or clarification.

## Live GitHub state

- At the start of every run or resumption, query GitHub directly for the current repository, default and target branches, assigned issue, parent and child issues, latest bodies and comments, dependencies, linked PRs, reviews, checks, and relevant GitHub Project fields. Do not rely on a previously captured issue tree or project snapshot.
- Refresh the remote refs needed to compare code with the live target branch. Do not reset, overwrite, or clean the user's checkout merely to make it match the remote; use read-only inspection or an isolated worktree as appropriate.
- Before claiming an issue, selecting a next issue, editing a coordination board, opening or merging a PR, closing an issue, or reporting completion, re-read the affected live GitHub objects and verify that their state has not changed. Resolve concurrent changes instead of overwriting them.
- When local code, a handoff, cached context, or an exported board disagrees with GitHub, treat GitHub as authoritative for coordination state. Investigate code-state differences against the relevant remote commits before proceeding, and surface genuine ambiguity rather than guessing.
- If live GitHub cannot be reached or authenticated, do not make coordination or implementation decisions from a snapshot. Report the access problem and limit work to clearly labeled read-only preparation until live state can be verified.

## Commit identity and attribution

- Use the repository's existing configured Git author and committer identity and the user's authenticated remote account for authorized pushes.
- Never add Codex, Claude Code, or other assistant co-author/sign-off trailers, generated-by footers, or AI-assistance attribution to commits, PRs, issues, or comments.
- Do not override `--author`, `user.name`, `user.email`, `GIT_AUTHOR_*`, or `GIT_COMMITTER_*`. If the configured identity is missing or unexpected, surface it before committing rather than inventing an identity.
- Inspect the final commit message for attribution injected by templates or hooks. Preserve required human DCO sign-offs and the user's existing cryptographic signing configuration.
- This rule controls identity and attribution; it does not independently authorize a commit, push, or merge.

## Start or resume

1. Read the assigned issue, parent chain, comments, dependencies, linked PRs, and relevant GitHub Project fields from live GitHub. Inspect relevant siblings for prior decisions; avoid loading unrelated branches.
2. Establish the goal, completion criteria, owner, and current execution state. Check for existing work before claiming a task or duplicating implementation.
3. Identify decisions and prerequisites affecting the task. Reopen settled decisions only with new evidence and explain the change.
4. Present the high-level implementation explanation to Ethan and satisfy the per-issue approval gate, unless a recorded explicit autonomous authorization covers this issue. After approval or verification of that authorization, post a short leaf comment with scope, approach, and assigned branch/worktree. On resumption, post meaningful changes rather than repeating the startup comment.
5. If blocked, record exactly what is needed and who can unblock it, if known. Continue independent work within scope rather than guessing requirements.

## Organize the tree

- Parent issues manage goals, children, owners, dependencies, blockers, shared decisions, and next ready actions.
- Aim for one focused, reviewable PR per implementation leaf. Split large leaves when independently testable work or unrelated decisions warrant it. Do not add hierarchy merely to reach a depth target.
- Group related leaves under the parent whose decisions they share. Respect existing issue/PR structure rather than mechanically restructuring it.
- When parallel execution is authorized, use separate worktrees and explicit ownership for independent tasks. Start dependent implementation only after prerequisites are available and verified.
- Choose fresh sessions based on complexity and coupling, not a fixed number of issues. Persist handoffs before retiring sessions.

## PR links to project-board issues

- Whenever creating a PR (including a draft) for work tracked on a GitHub Project board, link the PR to the corresponding issue on that board as part of PR creation. Adding the PR to the board or mentioning the issue in a comment does not satisfy this requirement; establish GitHub's native issue–PR relationship.
- Use a supported GitHub linking mechanism. Use closing keywords only when the PR completes the issue and automatic closure is appropriate; otherwise link through GitHub's Development/linked-issue controls without implying completion.
- Verify the relationship on live GitHub after creation and before reporting the PR ready or merging it. On resumption, repair a missing link for the current PR. Keep the leaf and parent coordination board's PR links current. If linking fails, report the specific blocker and leave the linking step explicitly incomplete.

## Implementer and worktree isolation

- Default all Init subagents to Sol (`gpt-5.6-sol`) unless the user or applicable instructions explicitly specify another model. Set the model explicitly when spawning; use a supported context mode that permits model selection rather than silently inheriting the main agent's model.
- Give every issue implementer the mandatory open/close workflow below when dispatching or resuming it. Do not rely on inherited conversation context or automatic skill discovery.
- Assign exactly one issue worktree to each implementer. Investigate code, edit files, run commands/tests, and commit only inside that assigned worktree. Do not cross into, edit, check out branches in, or run implementation commands against another issue's worktree or the root checkout.
- Verify the working directory and branch before edits or validation. Treat other worktrees and other contributors' changes as owned by them; never revert them.
- Bring prerequisites into the assigned worktree through the agreed Git integration path; never copy uncommitted work from a sibling worktree. If integration or a conflict needs coordination, raise it to the main agent.
- Treat each issue as its own task. Verify relevant parent/sibling decisions against the current issue and actual shared code. Do not carry implementation assumptions from previous issues unless they apply to shared code and are verified.
- Investigate, implement, write or update relevant tests, and run targeted validation. Run the full suite only when needed for the change or required by the repository.
- Return a brief summary: what changed, why, test results, and assumptions or limitations.

### Required skills in every implementer assignment

After the existing issue and delegation approval gates are satisfied, automatically include both [open-issue](../open-issue/SKILL.md) and [close-issue](../close-issue/SKILL.md) in each issue implementer's assignment. This applies to fresh agents, replacement agents, resumed agents, and any authorized recursive issue delegation. Research-only agents do not run implementation or closing workflows.

Resolve those links relative to this skill and pass their absolute paths. Verify both files are readable before dispatch. If the implementer runs in an environment without those paths, supply the full current skill contents in its assignment. Merely mentioning the skill names is not sufficient.

Use this assignment template, filling in the concrete issue, approved scope, worktree, and validation criteria:

```text
Implement <owner/repo>#<number> under the approved scope: <scope and approval or autonomous-authorization boundary>.
Your assigned worktree is <absolute path>, branch <branch>, targeting <base branch>.
You own <files/modules/responsibility>. You are not alone in the codebase: preserve others' changes, do not revert their work, and coordinate overlapping changes with the main agent.
Acceptance criteria: <criteria>. Validation: <required checks>.

Read <absolute path to open-issue/SKILL.md> and <absolute path to close-issue/SKILL.md> before implementation. Follow $open-issue <number> to rebuild live issue/parent/sibling context and post the session plan before editing code. Reuse your assigned worktree; do not create a second worktree or choose a different base. Work only on this issue.

Before returning a completed, partial, blocked, split, or low-context session, follow $close-issue <number>: push applicable work, create or update the PR and review guide, record the issue handoff, and update the parent and affected siblings. Return the PR link and head commit, session-plan and closing-comment links, validation results, remaining work, and blockers. If a step fails, identify it explicitly and return any unsaved handoff text.

Apply the Init integration rules supplied below. Do not merge, close the issue, delete the worktree, or start another issue. Return to the main agent for review. Report unanswered human questions or scope changes to the main agent; do not treat newly split issues as approved for implementation.
```

Include these integration rules in the assignment alongside the template; they reconcile the standalone skills with Init without changing their standalone behavior:

- Init's existing approval, authorization, identity/attribution, worktree isolation, native PR linking, main-agent review, merge, and cleanup rules remain in effect. Supply the applicable rules from this file with the assignment; do not make the implementer infer them from unavailable parent context.
- Use the open/close skills' plan and handoff content, but omit their `**[agent]**` prefix under Init's no-assistant-attribution convention. When reading prior sibling decisions, recognize existing session-close and decision comments with or without that prefix.
- Use the assigned validation scope and repository requirements. Run a baseline before implementation and final validation before handoff; Init's rule determines whether the full suite is needed. Report failed or unavailable checks.
- Include closing keywords only when the PR completes the issue and automatic closure is appropriate. Partial PRs must still have the native issue–PR relationship required by Init without implying completion.
- The close skill ends the implementer's session. Its standalone human-merge and human-cleanup language does not remove Init's existing main-agent merge and cleanup authorization. Implementers still perform neither action.

For a review-fix continuation on the same issue, resend both skill paths and the applicable integration rules, refresh changed live context, and update the plan/handoff with meaningful changes instead of duplicating unchanged comments. The implementer must complete the close workflow again before returning the revised PR head.

## Main-agent review

The main agent reviews the Git diff and the implementer's summary. Do not dispatch a separate review subagent. Open surrounding code only to verify a specific concern.

- Check correctness, regressions, missed edge cases, security, and missing test coverage.
- For diffs over roughly 100 lines, also check for unnecessary abstractions, wrappers, dependencies, or dead code that can safely be removed. Preserve correctness.
- Skip style nits, speculative concerns, and unrelated pre-existing issues. A quick skim is sufficient for trivial changes.
- Send only specific actionable findings back to the implementer; do not edit the code yourself unless Ethan explicitly authorizes it. After the implementer returns a fix, run the smallest relevant validation and check the finding is resolved. Repeat broader review only if the fix materially changes the implementation.
- Verify the implementer posted its session plan and completed the close workflow on live GitHub, including the PR review guide, issue handoff, and applicable parent/sibling updates. Have the implementer finish missing steps before treating its handoff as complete. The main agent then updates final review/merge state and the coordination board without duplicating the implementer's comments.

## Main-agent merge authorization

For an issue Ethan has explicitly approved for implementation, or one covered by his explicit autonomous authorization, the main agent may merge its PR into the agreed target branch without asking for a separate merge approval once it determines the work is ready. Implementers must return their work for main-agent review, not merge on their own. An explicit hold or request for Ethan's final approval overrides this standing permission.

- Confirm the issue's acceptance criteria are satisfied, main-agent review has no unresolved blocking findings, targeted validation passes, and all required checks and repository approvals are satisfied for the current PR head. Green CI alone is not review approval.
- Verify the repository, target branch and reviewed head commit immediately before merging; use a head-commit guard where supported. If the head changes, review the new changes and recheck validation before merging.
- Use the repository's permitted merge method and normal branch protections. Never bypass checks, required reviewers or a merge queue. If blocked, report the specific blocker rather than forcing a merge.
- Verify the actual merged state before reporting completion, update the leaf and parent board, then follow the worktree-cleanup rules. Queued or auto-merge-enabled is not yet merged.

This permission covers only the approved issue's PR or a PR within the recorded autonomous boundaries. It does not itself authorize starting another issue, expanding scope, or performing separate production deployment/provisioning actions.

## Completed-worktree cleanup

Once an issue is reviewed, merged into its target branch, and no dependent worktree still needs it, remove its worktree with `git worktree remove <exact-worktree-path>` from the coordinating checkout. Verify merge status, dependencies, and a clean worktree first. Never force removal or discard uncommitted changes; raise any such blocker to Ethan.

At the end, inventory worktrees and remove all completed, clean, unneeded issue worktrees. Keep active worktrees and any completed worktree still needed by a dependency; report why a retained completed worktree is needed. Do not remove the primary checkout or unrelated user worktrees.

## Parent issue as shared board

Reuse the parent's status section, or add a bounded `## Coordination board` section while preserving other content. Keep it current with:

- Goal and completion criteria.
- Child issue links, owners, statuses, and PR links.
- Dependencies and blockers.
- Shared decisions linked to their supporting discussions.
- Next ready tasks and required human actions.

Comments are the chronological discussion history. Update the board when status or decisions change. Read the latest body and comments before editing, preserve others' contributions, and merge concurrent changes. Avoid duplicate entries or comments on retries/resumption.

## Decisions on leaf and parent

On the leaf, record what was decided, why, supporting evidence or constraints, affected tasks/interfaces, and remaining uncertainty.

If a decision affects siblings or the overall plan, also post a brief summary on the relevant parent, linking the detailed leaf comment and affected issues. Keep task-local detail on the leaf.

Example:

> Decision: [what]. Reason: [evidence/constraint]. Affects: [issues/interfaces]. Follow-up: [if needed]. Details: [leaf comment link].

Distinguish proposals from accepted decisions. When a decision changes, add a comment identifying what it supersedes and why, then update the board. Preserve earlier discussion.

## Progress and blockers

Comment when a milestone completes, evidence changes the approach, a blocker appears or clears, or a PR becomes ready. Write plainly and briefly while retaining enough reasoning for someone outside the session. Avoid repetitive updates and raw logs; link useful evidence.

A blocker comment states what is blocked and why, what was tried, the exact action/decision needed, its owner if known, and work that can continue meanwhile.

## Finish or hand off

Before ending an implementation session, record on the leaf:

- What changed, with PR/commit links.
- Important decisions and rationale.
- Verification performed and results, including anything unverified.
- Remaining work, limitations, and blockers.
- The next action and issue that should pick it up.

Update the parent board with the leaf's state, shared decisions, and newly unblocked work. Distinguish implemented, verified, ready for review, and merged. Close issues only when completion criteria and repository closure rules are satisfied.

New agents enter through the assigned issue, read ancestors for direction, and inspect relevant siblings for evidence and prior decisions. The record should explain what happened, why, and what to do next without relying on the previous agent's memory.
