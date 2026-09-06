# Developer tooling (contributor scripts)

Loose scripts for repository contributors and CI. Not part of the Python
client product (`python-client/` holds the application) and not part of the
user-facing shell clients (`shell-clients/`).

| Directory | Purpose |
|---|---|
| `dev/` | local development environment setup (`setup_test_env.py`) |
| `test/` | local verification runs (`local_test.py`) |

Both scripts are plain Python 3 (stdlib only) and are idempotent. They run
against the test venv in WSL (`~/xray-venv`, see `docs/TEST-LOCAL.md`).