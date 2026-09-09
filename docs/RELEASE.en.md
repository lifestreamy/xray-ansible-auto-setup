> **Document:** `docs/RELEASE.en.md` · **Location:** `docs/` · **Version:** v0.3 · **Last updated:** 2026-09-05
>
> [Main README](../README.en.md) — project overview and quick start

# RELEASE — release policy

How the project ships releases: versioning, statuses and the check sequence before a release. The policy applies starting with v0.3.

## Purpose and scope

Contributions to the project are welcome (issues and pull requests on GitHub). The quality signals for releases are automated CI runs (GitHub Actions), operation on a production VPS, and user reports on stable releases (GitHub issues). There is no "alpha → beta → stable" ladder; a status is defined by the concrete criteria below.

## Versioning

- Versions are three-component `vX.Y.Z` (starting with v0.4.0; the old two-component tags are history and are not renamed).
- SemVer in the 0.x phase: a minor bump (`v0.3 → v0.4.0`) is a substantial change, breaking included (e.g. changing a CLI flag default); a patch (`v0.4.0 → v0.4.1`) is fixes, removals of experimental features and small renames (recorded in the CHANGELOG).
- The `v` prefix is required in all tags.

## Statuses and tags

Every release is pinned by an annotated git tag on a commit of the `staging` development line. No release branches are created.

Statuses — an explicit list:

- Code in `staging` without a tag is **not a release and has no status**; it may never become one.
- **experimental** — a shipped pre-release: tag `vX.Y.Z_experimental` + a GitHub Release with the pre-release flag, handed to manual operation — used on a production VPS, accumulating the promotion criteria. The experimental status is granted only after the pre-release is published.
- **stable** — all promotion criteria are met (see below); a second tag `vX.Y.Z_stable` on the same commit + the latest flag on the GitHub Release.

- Promoting does not change the commit: only the tag, the `Status` line in the CHANGELOG and the GitHub Release flag.
- If the next release ships before `vX.Y.Z` meets the stable criteria, the older one stays experimental — a normal outcome.
- The `v0.2_release` and `v0.3_experimental` tags use the old two-component naming — history, not renamed.

### Criteria for experimental → stable (all four)

1. A green full CI run on the release commit: distro matrix ubuntu 22.04 / 24.04 + debian 12, the firewall job, CLI tests and lint.
2. CI covers the client scenarios as fully as possible: the python client + the bash and PowerShell wrappers × ubuntu / windows / macos runners; missing coverage is built before promotion.
3. The maintainer has manually clicked through every usage scenario on a real VPS following the testing cheatsheets (`docs/TEST-LOCAL.en.md`, `docs/TEST-VPS.en.md`): deploy in two ways, rotation, client usability (responsiveness, translations, text clarity), real VPN traffic.
4. No known open regressions or hotfixes at the moment of promotion.

A calendar soak period is not a criterion (decision 2026-09-09): a deploy either fails immediately or works; the main risk lives in the deployment process and config generation, which the checks above cover.

## Release sequence

One release per version — after the whole planned version scope is done; no intermediate pre-releases for partially finished work (decision 2026-09-09).

1. The version scope (work waves) is complete in `staging`; each wave is pushed and verified by a green CI run before the next one starts.
2. `staging` is pushed manually; a green full GitHub Actions run is awaited on the head commit: workflow `molecule` (syntax, distro matrix, firewall job) and workflow `python-client` (CLI tests and lint). On failures — fix in separate commits and re-run until green.
3. One `docs: finalize vX.Y.Z` commit: `docs/PLANNED.*`, both CHANGELOG halves, `Version` / `Last updated` stamps of the public docs, the README summary and the statuses table row below.
4. The maintainer performs a successful manual deployment of the release content on a real VPS — the release is published only after that.
5. The PR from `staging` into `main` is merged with **Create a merge commit** (web rebase is prohibited — it recreates commits and strips signatures and dates).
6. The signed annotated tag `vX.Y.Z_experimental` is created on the merge node and pushed (by hand).
7. A GitHub Release is created: title — the tag name; body — the matching CHANGELOG section; experimental releases are marked pre-release, stable promotions — latest. Release assets are public files only; configs with keys never go into a release.

Tagging an unverified (not CI-green) commit is prohibited by the policy.

## Release statuses

The short sha is the verified code; its runs are visible in the repository's Actions history. A stable promotion updates the row (stable date) via the next finalize commit.

| Release | Verified code | Checked by CI | Status |
|---|---|---|---|
| v0.3 | `cf98f0b` | distro matrix (ubuntu 22.04 / 24.04, debian 12), firewall job, CLI tests and lint — 2026-09-05 | `v0.3_experimental` |

Note (2026-09-09): the promotion criteria changed — the calendar check "not before 2026-09-20" for v0.3 is void; v0.3 stays experimental, the next release is v0.4.0 (three-component format).

## CHANGELOG

- A pair of root files: `CHANGELOG.md` (RU) and `CHANGELOG.en.md` (EN); one `## [vX.Y.Z] — YYYY-MM-DD` section per release (Added / Changed / Fixed / Removed) with a `Status:` line. No auto-bump.
- Filled from commit messages at shipping time; both halves updated by the same commit with mirrored structure.

## Release commit

Its rules reduce to step 3 of the release sequence: `docs/PLANNED.*` (the "what is next" overview rewritten for the new version), public doc stamps, the README summary, both CHANGELOG halves. This document (`docs/RELEASE.en.md`), until a release ships, is edited by regular commits.
