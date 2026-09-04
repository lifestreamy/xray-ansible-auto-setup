> **Document:** `docs/RELEASE.en.md` · **Location:** `docs/` · **Version:** v0.3 · **Last updated:** 2026-09-04
>
> [Main README](../README.en.md) — project overview and quick start

# RELEASE — release policy and release acceptance

This document fixes how the project ships releases: versioning, release statuses, the pre-release test acceptance procedure, and where records of passed checks live. The policy applies starting with v0.3.

## Purpose and scope

The project is maintained by one person; there is no external tester base. The only honest "verified" signal is automated runs (local tests and CI on GitHub Actions) plus the author's personal acceptance on a production server. There is no "alpha → beta → stable by external feedback" ladder: a release status is defined by the concrete criteria below, not by expectations of tests this project will never have.

## Versioning

- SemVer in 0.x phase: a minor bump (`v0.3 → v0.4`) may contain breaking changes; a patch (`v0.3 → v0.3.1`) is bugfixes only.
- The `v` prefix is required in all tags.

## Statuses and tags

Every release is pinned by an annotated git tag on a commit of the `staging` development line. No release branches are created.

| Status | Tag | Meaning |
|---|---|---|
| experimental | `vX.Y_experimental` (patches: `vX.Y.Z_experimental`) | shipped right after test acceptance; used in production and accumulates trust |
| stable | `vX.Y_stable` — a second tag on the same commit | all promotion criteria below are met |

- Promoting does not change the commit: only the status changes — a new tag, the CHANGELOG status line, and the GitHub Release flag.
- If the next release ships before `vX.Y` meets the stable criteria, the older release stays experimental forever — that is a normal outcome, not a debt.
- Historical note: the `v0.2_release` tag predates this policy and used the old naming; it is not renamed.

### Criteria for experimental → stable (all three required)

1. A green full CI run on the release commit (distro matrix ubuntu 22.04 / 24.04 + debian 12, plus a separate firewall-task check).
2. The release has run on the author's production VPS for at least 14 days without hotfixes or regressions.
3. No known open regressions for the release at the moment of promotion.

## Pre-release acceptance procedure

A release `vX.Y` is shipped strictly in this order:

1. Work has accumulated in the `staging` development line.
2. `staging` is pushed to GitHub manually (by a human only; push automation is not provided).
3. Wait for a green GitHub Actions run on the top commit: matrix jobs per distribution plus the firewall job. On failures — fix in separate commits and re-run until green.
4. Fixation: a separate commit adds a record of the passed runs to the "Release acceptance" section below — links, matrix, dates. Such a commit touches nothing else (on first use — plus the README navigation line).
5. Only then the annotated tag `vX.Y_experimental` is created on the same commit and pushed next.
6. A GitHub Release is created: title — the tag name; body — the corresponding `CHANGELOG` section plus a link to the acceptance record below; experimental releases are marked pre-release, a stable promotion is marked latest. Release assets — public files only, never configs containing keys.

Tagging an unverified commit (without a green CI and without a fixation record) is prohibited by this policy.

## Release acceptance

Record format per release (newest first):

```text
### vX.Y — acceptance

- Date: YYYY-MM-DD
- GitHub Actions: <run URLs> — matrix ubuntu2204/ubuntu2404/debian12 + firewall job, green
- Local runs: scripts/test/local_test.py --runtime native (full cycle), <environment>, date — green
- Personal acceptance: <VPS>, date
- Verdict: experimental
```

First records arrive with the v0.3 release — the shipping procedure adds them in the format above.

## CHANGELOG

- Maintained as a pair of files in the repository root: [`CHANGELOG.en.md`](../CHANGELOG.en.md) (EN) and [`CHANGELOG.md`](../CHANGELOG.md) (RU).
- One section per release: `## [vX.Y] — YYYY-MM-DD` with Added / Changed / Fixed / Removed categories, a `Status:` line (experimental / `stable` since a date), and a pointer to the acceptance record in this document.
- Filled from commit messages only at shipping time; newest versions first; no auto-bump.
- Both halves of the pair are updated in the same commit with mirrored structure — this guards against RU/EN drift.

## Release commit

Shipping a version comes with a dedicated release commit that updates:

- `docs/PLANNED.md` and `docs/PLANNED.en.md` — the "what is next" overview rewritten for the new version (these two files are not edited outside the release commit);
- `Version` / `Last updated` stamps of all public documents;
- `README.md` / `README.en.md` — a "new since the previous version" summary;
- both halves of the `CHANGELOG`.

This document (`docs/RELEASE.*`) and the `CHANGELOG` are edited with regular commits until a release ships.
