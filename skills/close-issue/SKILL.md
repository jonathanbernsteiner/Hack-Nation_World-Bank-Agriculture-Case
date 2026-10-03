---
name: close-issue
description: End an agent session on one GitHub issue by opening or updating its PR, recording decisions and remaining work, and updating its parent epic and affected siblings. Use when wrapping up issue implementation or invoked as $close-issue with an issue number. Leaves merging and issue closure to humans.
metadata:
  created: "2026-04-20"
  updated: "2026-09-24"
---

# Close issue session

Usage: `$close-issue <issue-number>`.

You are ending your session on one GitHub issue. The next agent starts with zero memory of this session. Anything not written to GitHub is unavailable to that agent. Complete every applicable step below before stopping. If you are low on context, do the steps in order and abbreviate later sections rather than skipping earlier ones.

Resolve the issue number and repository from the invocation and session context. If ambiguous, ask the invoking user or coordinating agent. In commands below, set `issue_number`, `owner`, and `repo` to the resolved values. `$ARGUMENTS` in older invocations means the supplied issue number; it is not an automatically populated shell variable.

This workflow ends a session; it does not merge PRs or close GitHub issues. It applies to done, partial, blocked, and split-before-implementation outcomes. When invoked by a subagent, report the final status to its coordinating agent.

For multiline PR descriptions and comments, write the exact text to a temporary file and pass `--body-file <file>`. Keep newlines and literal code intact. Reuse session evidence where available and refresh live PR/issue state before reporting it.

## 1. Get the code into a PR

- Work from the assigned issue's worktree. Inspect its branch and diff, and identify the changes belonging to this session.
- Run the test suite. Record pass or fail, including any checks that could not run. Do not stop on a failure; report it and continue the handoff.
- Commit the issue's changes with a message that names the issue: `<summary> (#<issue-number>)`. Stage only the intended changes; do not include unrelated work or secrets.
- Push the branch. Open a PR if one does not exist using `gh pr create --repo "$owner/$repo" --title "<summary>" --body-file <file>`. Include `Closes #<issue-number>` in its body. If a PR already exists for this branch, push to it. Use a draft PR for partial or blocked implementation or failing required checks, and describe the remaining work.
- Do not merge. Do not close the issue. Humans merge, and the merge closes the issue.

If the session was blocked or split before implementation and there is no issue-related diff or existing PR, do not fabricate a commit or empty PR. Record `PR: none — <reason>` and continue with the issue handoff. If committing, pushing, or creating a PR fails, record the failure and local branch/commit needed for recovery, then continue the steps that remain possible.

## 2. Post the PR review guide

If a PR exists, comment on it:

```markdown
- What changed and why: <three to five sentences>
- Read in this order: <files, ordered so the reviewer sees the core change first>
- Riskiest part: <the one thing the reviewer should think hardest about>
- Verified by: <tests run, manual checks, commands and summarized output>
- Not verified: <anything you could not run or check>
```

## 3. Post the closing comment on the issue

This is the most important step. Comment on the assigned issue using `gh issue comment "$issue_number" --repo "$owner/$repo" --body-file <file>`:

```markdown
**[agent]** Session close

- Outcome: <done, partial, or blocked; one line explaining the status>
- PR: <link, or none with reason; include draft/open/merged state>
- Decisions made: <one bullet each: what was decided, alternatives rejected, why. Include anything a future agent might be tempted to undo>
- Deviations from the session plan: <what changed and why, or none>
- Interfaces changed: <function signatures, schemas, config keys, API shapes, or file layouts that other issues depend on; old vs new>
- Gotchas: <environment quirks, flaky tests, misleading names, incorrect docs, and other things that would cost the next agent time>
- Not done: <remaining work inside this issue's scope, if partial>
- Follow-up issues created: <#N: title, or none>
- Open questions for human: <questions only a person can answer, each with the decision it blocks, or none>
- Context worth copying to the vault: <anything the team should keep outside GitHub, or none>
```

Write for a reader who has never seen this repo. Prefer file paths, function names, and commands over vague prose. Include branch/worktree location and recovery instructions when work remains local or incomplete. `Done` means implementation and required verification are complete; explicitly state when human review or merge is still pending. Do not describe an unmerged PR as shipped. For a split issue, record the new children and the remaining implementation as partial.

## 4. Update the parent epic

Find the parent through the GraphQL `parent` field, or the `Parent: #N` line in the issue body. Use the parent identified during `$open-issue` if still current. Do not interpret an API failure as an absent parent.

```bash
gh api graphql -f owner="$owner" -f repo="$repo" -F number="$issue_number" -f query='
query($owner: String!, $repo: String!, $number: Int!) {
  repository(owner: $owner, name: $repo) {
    issue(number: $number) { parent { number title } }
  }
}'
```

If there is a parent, comment on it:

```markdown
**[agent]** #<issue-number> <done | partial | blocked>. <One sentence on what was implemented, with PR link and whether merge is pending.> <One sentence on anything that changes the epic's ordering or dependencies, or "no dependency changes".>
```

If the epic body has a checklist, check the box for this issue only if the PR is merged. Otherwise leave it. Preserve all unrelated content when editing the body. If no parent exists, note that in the handoff.

## 5. Warn affected siblings

Use the sibling context collected during `$open-issue`, or list the parent's native sub-issues and issue links. Retrieve all pages when necessary. For each sibling that depends on this issue, or consumes an interface you changed, comment:

```markdown
**[agent]** Heads up from #<issue-number>: <the specific change, old vs new, and where to look>. <PR link and whether it is merged or still pending.>
```

Skip only if nothing you changed is consumed by another issue. Do not tell a dependent issue it is unblocked merely because this session is done; report actual merge and dependency state.

## 6. Leave the workspace clean

- Aim for no uncommitted changes from this session. Commit intended issue work. Remove only disposable, session-created files that must not be committed, and say what was removed in the closing comment.
- Do not delete pre-existing, unrelated, or valuable uncommitted work to make `git status` clean. Preserve it and report the exact remaining paths and reason.
- Check `git status` and confirm the issue branch's commits are pushed. Report any exceptions or push failures instead of claiming a clean, pushed state. If an exception is discovered after the closing comment, add a correction to the issue.
- Do not delete the worktree. The human does that after merge.

## 7. Stop

End the session with the outcome, issue and PR links, verification result, and any blocker or required human action. Do not start the next issue. A new agent will be spawned for it.

If GitHub updates fail, return the unsaved handoff and identify which comments or updates were not posted. Never imply that local text was successfully written to GitHub.
