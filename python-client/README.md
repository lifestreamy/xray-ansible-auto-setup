# `python-client/`

Основной клиент `xrayvpn` (Python) — развертывание, обновление и ротация Xray-сервера.
Одинаково на Windows, Linux и macOS; две схемы исполнения за одним CLI.

## Установка и запуск

Нужен [uv](https://docs.astral.sh/uv/) (или Python 3.12+):

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"   # Windows
```

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh                                       # Linux/macOS
```

Из корня репозитория:

```bash
uv run --project python-client xrayvpn --help
```

Внутри `python-client/` (после `uv sync`) работают и `uv run xrayvpn ...`, и `python -m xrayvpn`.
На Windows можно вообще без флагов: двойной клик по `xrayvpn-deploy.pyw` открывает консоль и
запускает локальное развертывание (имя через дефис обязательно — `xrayvpn.pyw` рядом с пакетом
перехватывал бы `import xrayvpn` на Windows).

## Две схемы исполнения

- **remote** (`--execution remote`) — клиент сам поднимает окружение на VPS по SSH:
  бустрап, загрузка репозитория tarball'ом (GitHub серверу не нужен), playbook, забор
  готовых конфигов клиентов.
- **local** (`--execution local`) — playbook прогоняется на этой машине: на Linux напрямую,
  на Windows — через WSL (`uv` и venv на стороне дистрибутива клиент находит/создаёт сам,
  вenv по умолчанию `~/xray-venv`).
- Без `--execution` — вопрос в терминале (по умолчанию local).

## Примеры

```bash
# VPS по IP: пароль спросит скрыто (или заранее --pkey ~/.ssh/id_ed25519)
uv run --project python-client xrayvpn deploy --execution remote --host 1.2.3.4

# параметры подключения из личного inventory.yml
uv run --project python-client xrayvpn deploy --execution remote --use-inventory

# локально, без WARP и без принудительной ротации
uv run --project python-client xrayvpn deploy --execution local --no-warp --no-rotate

# план remote-развертывания без какого-либо подключения
uv run --project python-client xrayvpn deploy --execution remote --host 1.2.3.4 --dry-run
```

## Флаги `deploy`

- Режим: `--execution local|remote`.
- Переопределения сервера (иначе берётся из `config/settings.yml`): `--runtime native|docker|podman`,
  `--xray-port`, `--num-clients`, `--camouflage-domain`, `--warp/--no-warp`,
  `--rotate/--no-rotate` (перегенерация ключа REALITY и UUID / оставить как есть),
  `--manage-firewall/--no-firewall`.
- Инвентарь: `--inventory PATH` — только local, готовый файл вместо генерируемого;
  `--use-inventory` — только remote, читает подключение и переменные из личного `inventory.yml`
  (перекрывает host/key-флаги с предупреждением).
- Подключение (remote): `--host`/`-H`, `--user`/`-u` (default `root`), `--port`/`-p` (default 22),
  `--pkey FILE` (предпочтительно), `--pass TEXT` (пароль в открытом виде, хуже ключа; без него —
  скрытый запрос).
- Результат: `--clients-dir PATH` — куда сохранить конфиги клиентов
  (default `<repo>/downloaded-clients/`, забираются с сервера из `/root/vpn-configs`).
- Уборка на сервере (remote): по умолчанию staging-каталог удаляется, venv остаётся;
  `--full-cleanup` — снести и venv, `--no-cleanup` — оставить всё.
- Диагностика: `--dry-run` (local: ansible `--check`; remote: план без подключения),
  `--debug` / `--verbose` (Ansible -vvv/-vvvv; вместе нельзя, как и `--pkey` с `--pass`).

Полная афиша: `xrayvpn deploy --help`.

## Где что лежит

- `src/xrayvpn/` — пакет (`cli/`, `core/`, `core/execution/`, `core/transport/`);
- `tests/` — pytest-набор (в CI нога `python-client` гоняет его и ruff; есть и статический
  контракт `xrayvpn-deploy.pyw` ↔ CLI);
- смежные зоны репо: `shell-clients/` (Bash/PowerShell, поддержка без развития), `scripts/`
  (инструменты разработки).

Настройка сервера — [../docs/SETUP.md](../docs/SETUP.md), ротация ключей —
[../docs/ROTATION.md](../docs/ROTATION.md).
