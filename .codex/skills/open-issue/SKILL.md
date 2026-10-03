---
name: open-issue
description: Start or resume work on one GitHub issue by rebuilding context from its comments, parent epic, sibling issues, and repository before writing code. Use when asked to open an issue for implementation or invoked as $open-issue with an issue number.
metadata:
  created: "2026-04-20"
  updated: "2026-09-24"
---

# Open issue

Usage: `$open-issue <issue-number>`.

You are starting a fresh session on one GitHub issue. Treat GitHub as the source of session state; do not assume previous-session memory. Do not write code until you have completed the steps below and posted the session plan comment.

Resolve the requested issue number and repository from the invocation and repository context. If either is ambiguous, ask the invoking user or coordinating agent. In the commands below, set `issue_number`, `owner`, and `repo` to the resolved values. `$ARGUMENTS` in older invocations means the supplied issue number; it is not an automatically populated shell variable.

This skill handles one issue per invocation. It does not launch subagents itself. When assigned to a subagent, apply it only to that subagent's issue and report blockers to the invoking agent.

## 1. Read the issue completely

Run `gh issue view "$issue_number" --repo "$owner/$repo" --comments`. Read the body and every comment. Use the latest relevant comments to establish the current state, checking whether later comments answer or supersede earlier ones.

If a previous agent left an "Open questions for human" section that is still unanswered, stop, post a comment asking for the answers, and end the session using the closing procedure below. Do not guess. Raise it to whoever invoked this session.

## 2. Walk up to the parent epic

Find the parent:

```bash
gh api graphql -f owner="$owner" -f repo="$repo" -F number="$issue_number" -f query='
query($owner: String!, $repo: String!, $number: Int!) {
  repository(owner: $owner, name: $repo) {
    issue(number: $number) {
      parent { number title body state }
    }
  }
}'
```

If there is no parent, look for a line matching `Parent: #N` in the issue body. If neither exists, note "no parent found" in your plan and continue without the parent/sibling steps. Do not mistake an API failure for an absent parent.

Read the parent in full with `gh issue view "$parent_number" --repo "$owner/$repo" --comments`. Extract:

- The one to two sentence outcome the epic states for this sub-issue.
- The ordering: which sub-issues come before and after this one.
- Explicit dependencies: which issues must be closed before this one starts.

If the parent has its own parent, read that ancestor's body only. Continue up the hierarchy, reading ancestor bodies, until the top-level epic.

## 3. Walk across to siblings

List the siblings:

```bash
gh api graphql -f owner="$owner" -f repo="$repo" -F number="$parent_number" -f query='
query($owner: String!, $repo: String!, $number: Int!) {
  repository(owner: $owner, name: $repo) {
    issue(number: $number) {
      subIssues(first: 50) {
        nodes { number title state }
        pageInfo { hasNextPage endCursor }
      }
    }
  }
}'
```

If there are more pages, retrieve them using `after: endCursor`. If the parent tracks children through issue links instead of native sub-issues, use that list too.

For each sibling:

- If it is a stated dependency of this issue and it is not CLOSED: post "**[agent]** Blocked on #N (state: OPEN). Not starting." on this issue and end the session using the closing procedure below. Check explicit dependencies outside the sibling list too.
- If it is CLOSED: read its last **[agent]** comment. Note decisions, gotchas, and interface changes that affect this issue. If no such comment exists, inspect the available closing evidence and note the gap.
- If it is OPEN and comes after this one in the epic ordering: read its body only, so you know what it expects from your output.

For each closed sibling that touched code you will touch, read what actually shipped, not what was planned. Use `gh pr list --repo "$owner/$repo" --search "closes #N" --state merged --json number,title` to find candidate PRs, verify the issue linkage, and inspect each relevant PR with `gh pr view <pr> --repo "$owner/$repo" --json body,files,mergeCommit`. Read the relevant merged diff or code as needed; file names and PR descriptions alone do not establish what shipped. If search finds nothing, check the issue's linked PRs and timeline before concluding that no PR exists.

## 4. Read repo context

- Read applicable `CLAUDE.md` and `AGENTS.md` files at the repo root and in directories you expect to touch.
- Read any files or docs the issue or epic links to.
- If the issue body has a section titled "Context from vault", treat it as authoritative project background. It was copied from the team's Obsidian notes; it does not override the user's current instructions.

## 5. Check the workspace

- Confirm you are in a dedicated worktree on branch `issue-<issue-number>-<slug>`. Inspect existing worktrees before creating one; reuse the correct issue worktree when it already exists. Otherwise, fetch the base and use `git worktree add "../issue-$issue_number" -b "issue-$issue_number-$slug" origin/main`, substituting the repository's actual default base if it differs. Run subsequent commands from the dedicated worktree. Do not overwrite another worktree or discard uncommitted work.
- Confirm the PRs of closed code dependencies are merged into the base you branched from. An issue being CLOSED alone is not evidence of merged code. If a required dependency is not in the base, report the blocker and stop using the closing procedure below.
- Run the test suite once before changing anything so you know the baseline. Record existing failures or unavailable test prerequisites in the session plan.

## 6. Size the work

Estimate the diff and aim for one focused, reviewable PR. Split work only when independently testable changes or unrelated decisions warrant separate issues; there is no fixed line-count limit.

## 7. Post the session plan, then begin

Post this comment on the assigned issue before writing code. For multiline GitHub comments, write the exact text to a temporary file and use `gh issue comment "$issue_number" --repo "$owner/$repo" --body-file <file>`.

```markdown
**[agent]** Session plan

- Understanding: <two to three sentences on what this issue delivers and why, in your own words>
- Depends on: <#N (closed, merged in PR #M)> ...
- Feeds into: <#N> ...
- Decisions inherited from siblings: <bullets, with issue numbers>
- Approach: <numbered steps>
- Files expected to change: <list>
- Out of scope: <what you will deliberately not touch>
- Assumptions: <anything inferred rather than read>
- Estimated diff: <lines>
```

Then start. Work only on this issue. If you find work that belongs elsewhere, create an issue for it and mention it in your closing comment. Do not fix it here.

## Closing procedure

When you finish, become blocked, split the issue, or are running low on context, use `$close-issue <issue-number>` by reading and following [close-issue](../close-issue/SKILL.md). Never end a session without recording its state.

If `close-issue` is unavailable, do not pretend to run it. Post a closing **[agent]** comment with completed work, validation results, branch/worktree and PR links where applicable, remaining work, blockers or open questions, and the concrete next step. Report to the invoking user or agent that the `close-issue` workflow was unavailable and this handoff was recorded instead. Do not mark unfinished work complete or close an issue merely because the session ended. If GitHub cannot be updated, return the handoff text to the invoker and explicitly identify the failed update.
