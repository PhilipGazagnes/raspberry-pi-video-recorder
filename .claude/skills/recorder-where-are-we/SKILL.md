---
name: recorder-where-are-we
description: Report where the Raspberry Pi Video Recorder project stands right now - Done / Doing / Next / Planned, plus blockers and loose ends - by reading git branches, the GitHub board, milestones, epics, issues and PRs. Read only. Use when the user asks "where are we", "status", "what's next", "what's in progress", or wants a project catch-up on this project.
---

# Where are we

Build a short, factual status report of the Raspberry Pi Video Recorder. **Read only**: never commit, push, edit issues or write files unless the user asks afterwards.

All planning lives in GitHub (no markdown epic docs): board, milestones, epics with sub-issues.

## 1. Gather (run independent commands in parallel)

Repo: `/opt/projects/raspberry-pi-video-recorder` (`PhilipGazagnes/raspberry-pi-video-recorder`). GitHub calls use the `PhilipGazagnes` account, the only one with the `project` scope (`gh auth switch --user PhilipGazagnes` if a call returns 404 or a missing-scope error). Use `rtk proxy` when a command's output looks truncated.

**Git**
- `git fetch --all --prune -q` then `git branch -a --sort=-committerdate --format='%(refname:short) %(committerdate:short) %(subject)'`
- Ahead/behind for each local and remote branch vs `main`: `git rev-list --left-right --count main...<branch>`
- `git log --oneline -20 main`
- `git status --short` (uncommitted / untracked work) and `git stash list`
- Branches already merged into main (`git branch --merged main`) = cleanup candidates

**GitHub**
- Board (project 2): `gh project item-list 2 --owner PhilipGazagnes --format json --limit 200` → group by `status` (Todo / In Progress / Done), note `milestone`, `priority`, `size`, labels
- Milestones: `gh api 'repos/PhilipGazagnes/raspberry-pi-video-recorder/milestones?state=all' --jq '.[]|"\(.number) \(.title) \(.state) open=\(.open_issues) closed=\(.closed_issues) due=\(.due_on)"'`
- Epics (label `epic`): `gh issue list --label epic --state all --json number,title,state,milestone`, then for each one `gh api repos/PhilipGazagnes/raspberry-pi-video-recorder/issues/<n>/sub_issues --jq '.[]|"\(.number) \(.state) \(.title)"'`
- Open PRs: `gh pr list --state open --json number,title,headRefName,isDraft,updatedAt`
- Recently closed issues (last ~14 days): `gh issue list --state closed --limit 20 --json number,title,closedAt,milestone`
- Spike results: when a `spike` issue is closed, read its last comments: they hold the go / no-go decision.

## 2. Classify

- **Done**: closed milestones/issues, board "Done", commits on `main` in the last ~2 weeks (or since the last finished epic).
- **Doing**: board "In Progress", open PRs, branches with commits not in `main`, uncommitted work.
- **Next**: Todo items in the current (lowest-numbered open) phase milestone, by priority (P0 → P2). A `spike` issue in that milestone comes first.
- **Planned**: later phase milestones and Backlog, one line per milestone with its count, not every issue.

Cross-check sources and flag mismatches (e.g. issue closed but board still "In Progress", epic closed with open sub-issues, branch with no issue, milestone with all issues closed but still open).

## 3. Report (in the terminal: dashboard first, details underneath)

Start with a heading and one sentence (current phase and overall state), then **one fenced code block** holding the at-a-glance dashboard below. Then the detail sections.

### Dashboard (inside a ``` block, monospace)

Four panels, separated by a blank line. Fill them with the real data; this is an example:

```
PHASES                                           closed/total
  1  Cleanup         ██████░░░░  3/5    ◀ now
  2  Chunked rec.    ░░░░░░░░░░  0/8
     Backlog         · 2 open

BOARD
  ┌─ Done (2 wk) ─┬─ Doing ───────┬─ Next ────────┬─ Planned ─────┐
  │ 3 issues      │ #6 extension  │ #8 docs       │ Phase 2   · 8 │
  │ last: #7      │               │               │ Backlog   · 2 │
  │ 2026-11-05    │               │               │               │
  └───────────────┴───────────────┴───────────────┴───────────────┘

BRANCHES                               vs main
  main      ●── e8290fe                 —
  feat/x    ●── 1a2b3c4                 2↑ 0↓
  fix/y     ●── 5d6e7f8  ✓ merged → delete?

HEALTH
  ⚠ 1 loose end   ✎ 2 uncommitted   ☰ 0 stashes   ⇄ 1 open PR
```

Drawing rules:
- Progress bars: 10 cells, `█` per closed tenth (round down, but full only when all closed), `░` for the rest. `✓` when the milestone is closed, `◀ now` on the current phase.
- Board columns: at most 5 rows each. Next = issue number + 1–2 word label (+ priority if set); overflow becomes `+N more`. Keep the box widths aligned.
- Branches: `n↑` = commits ahead, `n↓` = behind. Mark `✓ merged → delete?` for branches fully merged into main, `⚠ stale` for no commit in 30+ days. List only local branches plus remote-only ones.
- Health: one line of counters. Omit a counter when it is 0, except open PRs.
- Keep the dashboard under ~30 lines, and no wider than ~80 columns.

### Details (normal markdown, under the dashboard)

```
## Done (last ~2 weeks)
## Doing
## Next
## Planned
## Loose ends   (mismatches, stale/merged branches, uncommitted files, blockers)
```

Rules: bullets, one line each, with `#issue` numbers and branch names. Don't repeat what the dashboard already shows: add the detail it can't (titles, why, links between items). Facts only, no guessing — say "unknown" when a source is missing. Keep the details under ~30 lines. End with at most 1-2 suggested next actions.
