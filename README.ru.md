# Развёртывание Xray Reality VPN-сервера

[English](README.md) | [Русский](README.ru.md)

Это Ansible-настройка для развёртывания Xray VLESS + REALITY VPN-сервера на удалённом VPS.
Генерирует клиентские конфиги: Clash Verge / FlClash (Mihomo Meta YAML) и Amnezia VPN (JSON).
Clash Verge и FlClash — основные клиенты на каждый день. Amnezia — вторичный вариант с известными ограничениями.

## Где запускается

- Linux: через bash-обёртку, либо напрямую `ansible-playbook` (тогда клиентские конфиги сам не скачивает).
- Windows: PowerShell-обёртка + WSL.

---

## Что делает

- Поднимает на свежем Ubuntu/Debian VPS Xray-core VPN-сервер с протоколом VLESS и транспортом REALITY (режим стелс).
- Генерирует клиентские конфиги и копирует их к вам: Clash Meta YAML для Clash Verge / FlClash, JSON для Amnezia.
- После прогона убирает локальную временную рабочую папку. В режиме `--full-cleanup` дополнительно сносит пакеты, которые сам поставил. На VPS после настройки ничего не откатывает.

## Требования

**Локальная машина:**

Linux:
- Ubuntu/Debian (или любой дистрибутив с `apt`).
- SSH-доступ к VPS.

Windows:
- WSL2 с Ubuntu/Debian (заранее установлен).
- PowerShell 5.1+ (встроен в Windows 10/11).

**VPS:**
- Свежий Ubuntu 20.04+ или Debian 11+.
- Root или sudo.
- Публичный IP.

Обёртка сама доустанавливает Python 3, Ansible и `sshpass`, если их нет. На Windows нужен только WSL.

## Быстрый старт

В минимальном случае нужны только IP VPS и пароль. Остальное скрипт сделает сам.

### Linux / WSL (Bash)

Полная справка: `./provision-vpn.sh -h`

```bash
# SSH-ключ; пароль из ключа.
./provision-vpn.sh -H 1.2.3.4 --pkey ~/.ssh/id_rsa

# Только хост. Пароль будет скрыто запрошен интерактивно.
./provision-vpn.sh -H 1.2.3.4

# Режим inventory: используется предзаполненный inventory.yml.
./provision-vpn.sh --use-inventory
```

### Windows (PowerShell)

Полная справка: `Get-Help .\Provision-VPN.ps1 -Full`

```powershell
# SSH-ключ (Windows-путь; обёртка сама переведёт в WSL-путь).
.\Provision-VPN.ps1 -HostName 1.2.3.4 -PKey C:\Users\You\.ssh\id_rsa

# Только хост. Пароль будет скрыто запрошен интерактивно.
.\Provision-VPN.ps1 -HostName 1.2.3.4

# Режим inventory.
.\Provision-VPN.ps1 -UseInventory
```

## Конфигурация

### Вариант 1: CLI-параметры

```bash
./provision-vpn.sh -H <VPS_IP> -u <SSH_USER> -p <SSH_PORT> --pkey <PATH_TO_KEY>
```

Аутентификация: SSH-ключ, пароль, или интерактивный запрос пароля (скрытый). `--pkey` и `--pass` взаимоисключающие.

### Вариант 2: Inventory-файл

Заполните `inventory.yml` и запустите с `--use-inventory`:

```yaml
all:
  hosts:
    your_host:
      ansible_host: 1.2.3.4
      ansible_user: root
      ansible_port: 22
      ansible_ssh_private_key_file: /path/to/key
      # ansible_ssh_pass: (используйте, только если нет SSH-ключа)
```

Оставьте только одно из `ansible_ssh_private_key_file` или `ansible_ssh_pass`. Указать оба — ошибка.

В режиме inventory обёртка читает значения из `inventory.yml` и игнорирует все CLI-параметры подключения и аутентификации. На Windows пути к ключам в `inventory.yml` должны быть валидны из WSL (например, `/mnt/c/Users/You/.ssh/id_rsa`).

## Параметры

### Bash-скрипт

| Флаг | Описание | Обязательно |
|------|----------|-------------|
| `-H, --host` | IP / хост VPS | Да (режим CLI) |
| `-u, --user` | SSH-пользователь | Нет (по умолчанию: `root`) |
| `-p, --port` | SSH-порт | Нет (по умолчанию: `22`) |
| `--pkey` | Путь к приватному SSH-ключу | Нет* |
| `--pass` | SSH-пароль | Нет* |
| `--use-inventory` | Использовать `inventory.yml` вместо CLI-аргументов | Нет |
| `--clients-dir` | Локальная папка для скачанных клиентских конфигов | Нет |
| `--cleanup` | Удалить временную рабочую папку (по умолчанию) | Нет |
| `--full-cleanup` | Удалить рабочую папку и пакеты, которые скрипт поставил | Нет |
| `--no-cleanup` | Сохранить рабочую папку для отладки | Нет |
| `--debug` | Ansible `-vvv` + `xray_debug=true` | Нет |
| `--verbose` | Ansible `-vvvv` + `xray_debug=true` | Нет |
| `--dry-run` | Прогон в режиме симуляции внутри WSL, без изменений | Нет |

\* `--pkey` и `--pass` взаимоисключающие. Если не указан ни один, скрипт скрыто запросит пароль.

### PowerShell-скрипт

Те же флаги в PowerShell-стиле плюс два дополнительных:

- `-HostName` вместо `--host`
- `-PKey` вместо `--pkey`
- `-Pass` вместо `--pass`
- `-UseInventory` вместо `--use-inventory`
- `-ClientsDir` вместо `--clients-dir`
- `-CleanupMode` (`Default`, `Full`, `None`)
- `-LogLevel` (`None`, `Default`, `Verbose`)
- `-DryRun` — запускает bash-скрипт с `--dry-run` внутри WSL. Никаких системных изменений.

`-PKey` принимает приватный ключ в OpenSSH-формате, читаемый из WSL. PuTTY-файлы `.ppk` не поддерживаются.

## Результат

Локальная машина:
- Linux: `./downloaded-clients/*.json` и `./downloaded-clients/*.yaml`
- Windows: `.\downloaded-clients\*.json` и `.\downloaded-clients\*.yaml`

VPS:
- `/root/vpn-configs/*.json` (Amnezia) и `/root/vpn-configs/*.yaml` (Clash Verge / FlClash)

Рекомендуемый клиент: импортируйте `clash_client_*.yaml` в Clash Verge (Windows/macOS/Linux, режим TUN) или FlClash (Android).

Вторичный, с оговорками: Amnezia `client_*.json` есть, но с известными проблемами — Windows split-tunnel может обрушить сетевой стек, Android keepalive и фоновая работа ненадёжны. Используйте Clash Verge или FlClash, если вам не нужен именно Amnezia.

Ссылки:
- Clash Verge: https://github.com/clash-verge-rev/clash-verge-rev
- FlClash: https://github.com/chen08209/FlClash
- Amnezia: https://github.com/amnezia-vpn/amnezia-client

## Расширенная конфигурация

Для детального контроля правится `group_vars/all.yml`:

```yaml
num_clients: 3                        # Сколько VPN-профилей генерировать
reality_camouflage_domain: dl.google.com  # Домен для REALITY-обфускации
warp_enabled: true                    # Включить исходящее подключение через Cloudflare WARP
```

- `num_clients`: сколько клиентских конфигов генерировать. У каждого свой UUID. Увеличение числа добавляет UUID в постоянное хранилище; уменьшение только прячет «лишние» из сгенерированных конфигов.
- `reality_camouflage_domain`: легитимный домен, куда REALITY перенаправляет подозрительные соединения, чтобы VPN-трафик выглядел как обычный HTTPS.
- `warp_enabled`: включает исходящее подключение через Cloudflare WARP. Тумблер только через конфиг — отдельного CLI-флага для него нет.

## Закреплённый образ и WARP IPv4

Docker-образ Xray закреплён на `teddysun/xray:26.6.27` (проверенная версия). `:latest` намеренно не используется — автообновление до 26.7.11 в июле 2026 сломало совместимость VLESS+REALITY. Для осознанного обновления поменяйте `xray_docker_image` в `group_vars/all.yml` (тег или `sha256:…`-дигест), протестируйте, затем разверните.

Исходящее подключение WARP (`warp_ipv6: false`) по умолчанию IPv4-only — это для совместимости с VPS, у которых нет IPv6-маршрута. В таком режиме WireGuard-интерфейс использует только IPv4. `warp_endpoint: "162.159.192.1:2408"` — это Cloudflare WARP IPv4-anycast (стабильное имя `engage.cloudflareclient.com:2408`). При необходимости переопределите в `group_vars/all.yml`.

`warp_enabled: true` требует `wgcf` 2.2.22, который роль скачивает сама. Постоянные учётные данные WARP — это `wgcf-account.toml` и `wgcf-profile.conf` в `/root/xray-config/`.

## Персистентная идентичность

REALITY-ключи, short ID и клиентские UUID сохраняются в `/root/xray-config/reality-state.json` (режим `0600`). Обычные повторные запуски сохраняют существующую идентичность — клиентские конфиги остаются стабильными.

Чтобы выполнить ротацию, поставьте `xray_reality_rotate: true` в `group_vars/all.yml` (или передайте `-e xray_reality_rotate=true`). Старое состояние сначала бэкапится с меткой времени, потом генерируется новая идентичность. После успешного прогона верните тумблер в `false`. Полный runbook — в [docs/SECRET_ROTATION.md](docs/SECRET_ROTATION.md).

## Безопасность

- Чувствительные файлы (`config.json`, `reality-state.json`, WARP-профили) — режим `0600` (только root).
- Клиентские конфиги в `/root/vpn-configs/` — режим `0640`.
- Реальные приватные ключи и клиентские UUID хранятся только в `/root/xray-config/reality-state.json` — в клиентские конфиги они не попадают.
- `--debug` и `--verbose` печатают дополнительные диагностические сообщения, включая `private_key` и `client_uuids` из `reality-state.json`. Используйте осознанно и не пересылайте такие логи.

## Проверка после развёртывания

После прогона роль выполняет небольшой набор non-fatal проверок: контейнер использует закреплённый образ, Xray-порт слушает локально, в журнале Xray нет очевидных ошибок. Эти проверки не валидируют REALITY-хендшейк и не проверяют WARP-маршрутизацию. Подтвердите их реальным клиентом извне VPS.

Ротация секретов — в [docs/SECRET_ROTATION.md](docs/SECRET_ROTATION.md).

## Дополнительные примеры

```bash
# Нестандартный SSH-порт и папка для конфигов.
./provision-vpn.sh -H vps.example.com -p 2222 \
  --pkey ~/.ssh/id_rsa --clients-dir ~/vpn-configs

# Прогон в режиме симуляции: bash-скрипт выполняется внутри WSL с --dry-run. Без изменений.
./provision-vpn.sh -H 1.2.3.4 --pkey ~/.ssh/id_rsa --dry-run

# Полная очистка: убрать рабочую папку и пакеты, которые скрипт поставил.
./provision-vpn.sh -H 1.2.3.4 --pkey ~/.ssh/id_rsa --full-cleanup
```

## Windows и WSL

- Нужен WSL2 с Ubuntu/Debian. Обёртка вызывает bash-скрипт через WSL.
- `-PKey` принимает приватный ключ в OpenSSH-формате. Передавайте Windows-путь; обёртка сама переведёт его в `/mnt/<drive>/...` для WSL. PuTTY-файлы `.ppk` не поддерживаются.
- В режиме inventory обёртка передаёт bash-скрипту только `--use-inventory`. Путь к ключу в `inventory.yml` должен быть валидным из WSL. Для Windows-ключей используйте `/mnt/c/...`.
- `--clients-dir` по умолчанию — `.\downloaded-clients\` рядом со скриптом. Обёртка создаёт папку сама.
- `-Pass` нигде не логируется — даже при `-LogLevel Verbose` или `-DryRun`.

## Устранение неполадок

**"Command not found: ansible"**
Скрипт ставит его сам. Если не получилось:
```bash
sudo apt-get update && sudo apt-get install -y ansible
```

**"Permission denied (publickey)"**
Проверьте права ключа на той машине, где запускается обёртка:
```bash
chmod 600 ~/.ssh/id_rsa
```
Проверьте вручную: `ssh -i ~/.ssh/id_rsa user@host`.

**"inventory.yml missing required fields"**
Заполните все нужные поля в `inventory.yml` до запуска `--use-inventory`, либо используйте CLI-режим с `-H`, `--pkey`/`--pass`.

**Переносы строк (LF vs CRLF)**
Скрипты форсят LF через `.gitattributes`. Если всё равно странно: `dos2unix provision-vpn.sh`, переклонируйте репозиторий, или откройте issue.

## Участие в проекте

Вклад приветствуется. Соблюдайте conventional commits. Тестируйте с `--dry-run` и реальным прогоном на своём VPS, включая проверку подключения через настоящий клиент.

## Issues

Ошибка? Откройте issue с указанием: ваше окружение (Linux/Windows, версия bash/PowerShell), ожидаемое и фактическое поведение, шаги воспроизведения, релевантные логи.

Предложение? Откройте issue с указанием: как сейчас используете проект, что хотелось бы добавить, готовы ли сами протестировать.

## Лицензия

AGPL-3.0 с дополнительным пунктом о коммерческом использовании.
Свободно для личного использования и некоммерческого распространения.
Коммерческое использование — только с моего письменного разрешения: **tim.korelov@yandex.com**.
Полный текст: [LICENSE](LICENSE) (англ.). Краткое описание на русском: [LICENSE.ru.md](LICENSE.ru.md).

## Автор

Tim Korelov
https://github.com/lifestreamy
