# Contributing to NexusHomeLab

These rules apply to every repo in the org, whether a person or an agent wrote the
change. Most code here is written by agents, so history and PRs must explain
themselves to someone who didn't write them.

A repo's `AGENTS.md` adds what's specific to that repo (architecture, commands,
files not to touch) and links here for everything else.

## Enforced by GitHub

These can't be skipped. They're set in [`registry`](https://github.com/NexusHomeLab/registry),
which manages every repo's settings and rulesets.

- **Changes go through a PR.** Nobody pushes to `main`.
- **Every PR references an issue.** The required check `linked-issue / check` fails
  otherwise (see [Linking issues](#linking-issues)).
- **Required checks must pass.** Nobody can bypass them, the owner included.
- **One approval**, given after the last push. Review threads must be resolved.
- **Squash merge only, linear history.** One commit per PR lands on `main`.

## Conventions

GitHub doesn't check these, but reviewers (human and Claude) do.

### PR titles

Use [Conventional Commits](https://www.conventionalcommits.org/): `<type>: <summary>`,
lower case, no full stop. The title becomes the squashed commit on `main`, so get it
right.

| Type | For |
|---|---|
| `feat` | new behaviour |
| `fix` | a bug fix |
| `refactor` | restructuring with no behaviour change |
| `test` | tests only |
| `docs` | documentation only |
| `ci` | workflows and pipeline |
| `build` | build system, dependencies |
| `perf` | performance |
| `chore` | anything else |

### Branches

- `<type>/<issue>-<slug>`, e.g. `fix/42-retry-on-timeout`
- Agents use `agent/<issue>-<slug>`
- **Rebase, never merge.** To update a branch: `git fetch && git rebase origin/main`.
  Never merge `main` into a branch.

### PR description

The PR template has these sections. If you open PRs from the CLI or API, the template
isn't applied, so write them yourself:

- **What:** the change
- **Why:** the problem it solves
- **How it was tested:** commands run, what you checked
- **Risk:** what could break, and how far
- **What I'm unsure about:** anything a reviewer should look at closely
- **Issue:** see below

### Linking issues

| Write | When | Effect |
|---|---|---|
| `Closes #N` | this PR finishes issue N | issue N closes on merge |
| `Refs #N` | partial or related work | issue N stays open |
| `Refs NexusHomeLab/<repo>#N` | an issue in another repo | stays open |

`close`, `fix` and `resolve` (any tense) followed by an issue number close that issue
on merge, **anywhere in the description**, even mid-sentence. Only use them for the
issue the PR finishes.

### Issues

- Every issue has a **Done when**: something you can check, not "it works". The issue
  forms require it.
- One PR per issue where possible. Split big work into an epic with sub-issues.

### Code and tests

- **Every bug fix ships with a test** that would have caught it.
- No PR size limit, but a PR does one thing.
- Planning files that AI tools create (specs, plans, scratch) stay out of git; add
  their folders to `.gitignore`. Real design decisions go in `docs/adr/`.
