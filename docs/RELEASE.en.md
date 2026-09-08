> **Document:** `docs/RELEASE.en.md` · **Location:** `docs/` · **Version:** v0.3 · **Last updated:** 2026-09-05
>
> [Main README](../README.en.md) — project overview and quick start

# RELEASE — release policy

How the project ships releases: versioning, statuses and the check sequence before a release. The policy applies starting with v0.3.

## Purpose and scope

Contributions to the project are welcome (issues and pull requests on GitHub). The quality signals for releases are automated CI runs (GitHub Actions), operation on a production VPS, and user reports on stable releases (GitHub issues). There is no "alpha → beta → stable" ladder; a status is defined by the concrete criteria below.

## Versioning

- SemVer in the 0.x phase: a minor bump (`v0.3 → v0.4`) is a substantial change, breaking included; a patch (`v0.3 → v0.3.1`) is fixes, removals of experimental features and small renames (recorded in the CHANGELOG).
- The `v` prefix is required in all tags.

## Statuses and tags

Every release is pinned by an annotated git tag on a commit of the `staging` development line. No release branches are created.

Statuses — an explicit list:

- Code in `staging` without a tag is **not a release and has no status**; it may never become one.
- **experimental** — a shipped pre-release: tag `vX.Y_experimental` (patches: `vX.Y.Z_experimental`) + a GitHub Release with the pre-release flag, handed to manual operation — used on a production VPS, accumulating the promotion criteria. The experimental status is granted only after the pre-release is published.
- **stable** — all promotion criteria are met (see below); a second tag `vX.Y_stable` on the same commit + the latest flag on the GitHub Release.

- Promoting does not change the commit: only the tag, the `Status` line in the CHANGELOG and the GitHub Release flag.
- If the next release ships before `vX.Y` meets the stable criteria, the older one stays experimental — a normal outcome.
- The `v0.2_release` tag predates this policy and used the old naming; it is not renamed.

### Criteria for experimental → stable (all three)

1. A green full CI run on the release commit: distro matrix ubuntu 22.04 / 24.04 + debian 12, the firewall job, CLI tests and lint.
2. The release has run on the author's production VPS for 14+ days without hotfixes or regressions.
3. No known open regressions at the moment of promotion.

## Release sequence

1. Work has accumulated in `staging`.
2. `staging` is pushed manually; a green full GitHub Actions run is awaited on the head commit: workflow `molecule` (syntax, distro matrix, firewall job) and workflow `python-client` (CLI tests and lint). On failures — fix in separate commits and re-run until green.
3. One `docs: finalize vX.Y` commit: `docs/PLANNED.*`, both CHANGELOG halves, `Version` / `Last updated` stamps of the public docs, the README summary and the statuses table row below.
4. The annotated tag `vX.Y_experimental` is created on the finalize commit and pushed (by hand too).
5. A GitHub Release is created: title — the tag name; body — the matching CHANGELOG section; experimental releases are marked pre-release, stable promotions — latest. Release assets are public files only; configs with keys never go into a release.

Tagging an unverified (not CI-green) commit is prohibited by the policy.

## Release statuses

The short sha is the verified code; its runs are visible in the repository's Actions history. A stable promotion updates the row (stable date) via the next finalize commit.

| Release | Verified code | Checked by CI | Status |
|---|---|---|---|
| v0.3 | `cf98f0b` | distro matrix (ubuntu 22.04 / 24.04, debian 12), firewall job, CLI tests and lint — 2026-09-05 | `v0.3_experimental` |

## CHANGELOG

- A pair of root files: `CHANGELOG.md` (RU) and `CHANGELOG.en.md` (EN); one `## [vX.Y] — YYYY-MM-DD` section per release (Added / Changed / Fixed / Removed) with a `Status:` line. No auto-bump.
- Filled from commit messages at shipping time; both halves updated by the same commit with mirrored structure.

## Release commit

Its rules reduce to step 3 of the release sequence: `docs/PLANNED.*` (the "what is next" overview rewritten for the new version), public doc stamps, the README summary, both CHANGELOG halves. This document (`docs/RELEASE.en.md`), until a release ships, is edited by regular commits.
