> **Document:** `docs/SETUP.md` · **Location:** `docs/` · **Version:** v0.2 · **Last updated:** 2026-08-12
>
> [Главный README](../README.md) — обзор проекта и быстрый старт

# SETUP — настройка и эксплуатация

Ниже — переменные и шаги, которые реально влияют на поведение сервера. Разворачивал не раз, всё проверено.

Как подготовить VPS и локальную машину; какие переменные есть и как влияют на поведение; как проверить, что после развёртывания всё работает.

Полный глоссарий терминов — в [`docs/GLOSSARY.md`](GLOSSARY.md).

## Файлы конфигурации

| Файл | Что настраивает | Как влияет |
|---|---|---|
| `inventory.yml` (создаётся из `inventory.yml.example`) | Подключение к VPS: хост, пользователь, порт, ключ или пароль | Только для `--use-inventory`; CLI-режим собирает свой inventory сам |
| `config/settings.yml` | Все параметры сервера: `num_clients`, `reality_camouflage_domain`, `warp_enabled`, `xray_port`, `xray_docker_image` и остальные | Читается при каждом запуске Ansible playbook через `vars_files` |
| `deploy.yml` | Точка входа playbook | Обычно не трогается |

Какие параметры можно передать как CLI-флаги скрипта — только параметры подключения (`-H`, `-u`, `-p`, `--pkey`, `--pass`, `--use-inventory`, cleanup и verbosity). Остальная конфигурация — через `config/settings.yml`. Для набора самых частых параметров (runtime, порт, число клиентов, WARP, ротация) есть лёгкая CLI-обёртка `scripts/cli_deploy.py` — см. раздел «CLI-флаги `cli_deploy.py`» ниже.

## Runtime selector

`config/settings.yml` поддерживает три варианта развёртывания через переменную `xray_runtime`:

| `xray_runtime` | Что устанавливается | Когда выбирать |
|---|---|---|
| `native` (по умолчанию) | Xray-бинарь `/usr/local/xray/xray` под управлением systemd | Наименьший footprint (~10 МБ RAM); рекомендуемый вариант для новых развёртываний. |
| `docker` | Docker Engine + `teddysun/xray:26.6.27` через `xray.service.docker.j2` | Legacy escape hatch. Оставлен для совместимости со старыми deploy; не покрыт molecule-тестами. |
| `podman` | Podman + `ghcr.io/xtls/xray-core:26.6.27` через `xray.service.podman.j2` | Experimental; не покрыт molecule-тестами. |

Изменить runtime можно в `config/settings.yml` (`xray_runtime: native` → `docker` или `podman`) и перезапустить playbook. Дополнительные переменные:

- `xray_version: "26.6.27"` — единственный источник версии Xray-core. Не используйте `:latest` (Incident 2026-07-28: 26.7.11 сломал VLESS+REALITY+vision).
- `xray_container_repo: "ghcr.io/xtls/xray-core"` — репозиторий для `docker` и `podman`.
- `xray_docker_image` — escape hatch для override контейнерного образа; если не задан, используется derived `{{ xray_container_repo }}:{{ xray_version }}`.

Подробности дизайна и footprint-сравнение рантаймов — см. историю проекта.

## CLI-флаги `cli_deploy.py`

Для частых override'ов есть `scripts/cli_deploy.py` (stdlib argparse, MVP). Принимает:

- `--runtime {native|docker|podman}` — переопределяет `xray_runtime`.
- `--xray-port <int>` — переопределяет `xray_port`.
- `--num-clients <int>` — переопределяет `num_clients`.
- `--camouflage-domain <fqdn>` — переопределяет `reality_camouflage_domain`.
- `--warp` / `--no-warp` — `warp_enabled`.
- `--rotate` / `--no-rotate` — `xray_reality_rotate`.
- `--inventory <path>` — использовать существующий `inventory.yml` с реальным `ansible_host` (нужно для remote VPS, когда Ansible подключается по SSH).
- `--dry-run` — `ansible-playbook --check` (без применения изменений).

Пример:

```bash
python3 scripts/cli_deploy.py --runtime native --xray-port 443 --no-warp
```

Сгенерированный `inventory.yml` (gitignored) содержит только указанные override'ы; остальное по-прежнему берётся из `config/settings.yml`.

## Про проект

Это утилита, использующая Ansible для развёртывания Xray VLESS + REALITY VPN-сервера на удалённом VPS. Генерирует клиентские конфиги для Clash Verge / FlClash (Mihomo Meta YAML) и Amnezia VPN (JSON). Clash Verge и FlClash — основные рекомендуемые и протестированные клиенты. Amnezia — рабочий, но не рекомендуемый из-за нестабильности вариант. Для запуска на разных платформах используются скрипты-обёртки PowerShell и Bash (PowerShell вызывает bash)

## Что нужно знать перед началом

**VPS:**

- Свежий Ubuntu 20.04+ или Debian 11+.
- Root или sudo.
- Публичный IP.

**Локальная машина:**

Linux:

- Ubuntu/Debian (или любой дистрибутив с `apt`).
- SSH-доступ к VPS.

Windows:

- WSL2 с Ubuntu/Debian (заранее установлен).
- PowerShell 5.1+ (встроен в Windows 10/11).

Перед оплатой VPS на длительный срок — проверьте его через `carrox-vps-check` или `ipcheck-plus`. Подробности в [`docs/TEST-VPS.md`](TEST-VPS.md).

## Переменные `config/settings.yml`

<details>
  <summary>Все переменные (для технарей)</summary>

| Переменная | Что делает |
|---|---|
| `xray_runtime` | Runtime selector: `native` (по умолчанию), `docker`, `podman`. См. раздел «Runtime selector» выше. |
| `xray_version` | Единая версия Xray-core (по умолчанию `"26.6.27"`). |
| `xray_container_repo` | Репозиторий для `docker` / `podman` (по умолчанию `ghcr.io/xtls/xray-core`). |
| `num_clients` | Сколько клиентских конфигов сгенерировать (каждый со своим UUID). |
| `reality_camouflage_domain` | SNI легитимного сайта для маскировки REALITY (по умолчанию `dl.google.com`). Публичный параметр. |
| `xray_docker_image` | Override для контейнерного образа. По умолчанию derived из `xray_container_repo:{{ xray_version }}`. Закреплён на `teddysun/xray:26.6.27` для обратной совместимости. |
| `xray_config_dir` | Каталог состояния на VPS (`/root/xray-config`). |
| `xray_client_configs_dir` | Каталог сгенерированных конфигов на VPS (`/root/vpn-configs`). |
| `xray_port` | Порт inbound (по умолчанию `443`). |
| `warp_enabled` | Включить WARP outbound (`true` / `false`). |
| `warp_ipv6` | IPv6 в WireGuard (`false` — IPv4-only по умолчанию). |
| `warp_endpoint` | Cloudflare WARP endpoint (`162.159.192.1:2408`). |
| `warp_mtu` | MTU WireGuard (`1420`). |
| `warp_wgcf_version` | Версия wgcf (`2.2.22`). |
| `warp_wgcf_url` | URL для скачивания wgcf. |
| `xray_backup_enabled` | Резервные копии с меткой времени перед перезаписью (`true`). |
| `xray_reality_rotate` | Полная ротация REALITY. По умолчанию `false`. Подробности — в [`docs/ROTATION.md`](ROTATION.md). |

</details>

## WARP подробно

`warp_enabled: true` добавляет в Xray дополнительный исходящий туннель через Cloudflare WARP. Это нужно, чтобы скрыть IP вашего VPS от посещаемых сайтов — они будут видеть IP Cloudflare вместо вашего.

**IPv4-only по умолчанию.** Параметр `warp_ipv6: false` исключает IPv6-адрес из WireGuard-интерфейса. Это для совместимости с VPS без IPv6-маршрута. В этом режиме `allowedIPs` и `domainStrategy` остаются, но фактический туннель идёт только по IPv4. Если у вас есть рабочий IPv6 — поменяйте на `true`.

**Endpoint.** По умолчанию `162.159.192.1:2408` — это Cloudflare WARP IPv4-anycast. Стабильное имя — `engage.cloudflareclient.com:2408`. При необходимости переопределите в `config/settings.yml`.

**Требования.** `wgcf` 2.2.22. Роль скачивает бинарник сама при `warp_enabled: true`. Персистентные учётные данные — `wgcf-account.toml` и `wgcf-profile.conf` в `/root/xray-config/`.

**Проверка egress.** Проверяйте снаружи VPS, через реальный VPN-клиент, не через `curl` из контейнера Xray. С устройства, на котором запущен VPN-клиент:

```bash
curl -4 https://ifconfig.io   # должен вернуть IP Cloudflare (или IP VPS, если WARP выключен)
curl -4 https://cloudflare.com/cdn-cgi/trace   # альтернатива, ищите colo= и ip=
```

Подробности о ротации WARP — в [`docs/ROTATION.md`](ROTATION.md), раздел §4.

## Проверка после развёртывания

После любого прогона (без ротации и с ротацией) выполните ручную проверку.

Проверьте, что Xray запущен под выбранным runtime. Для `xray_runtime: native` (по умолчанию):

```bash
systemctl is-active xray                                       # должно вернуть 'active'
/usr/local/bin/xray version | head -n 3                         # бинарь отвечает
journalctl -u xray --no-pager -n 30 | grep -iE 'error|fail|panic'   # без явных ошибок
```

Для `xray_runtime: docker`:

```bash
docker inspect xray --format '{{ .Config.Image }}'             # закреплённый образ
docker inspect xray --format '{{ .State.Running }}'           # true
```

Для `xray_runtime: podman`:

```bash
podman inspect xray --format '{{ .ImageName }}'                # закреплённый образ
podman inspect xray --format '{{ .State.Running }}'           # true
```

Проверьте, что Xray-порт (`xray_port`, по умолчанию `443`) слушает на VPS:

```bash
nc -zv <VPS_IP> 443   # <VPS_IP> замените на свой; должно вернуть succeeded
```

Подключитесь хотя бы одним реальным клиентом (Clash Verge / FlClash / Amnezia) и проверьте, что трафик идёт через него.

Встроенные проверки роли покрывают только закреплённый образ, слушающий порт и очевидные ошибки журнала. Они не заменяют ручную проверку выше.

## Как добавить ещё клиентов без ротации

Если вы хотите добавить новый клиентский конфиг, не трогая существующие ключи — увеличьте `num_clients` в `config/settings.yml` и запустите playbook. Новые UUID добавятся в `reality-state.json`, новые конфиги появятся в `/root/vpn-configs/` на VPS и в `./downloaded-clients/` локально. Существующие клиенты продолжают работать.

## Лицензия

AGPL-3.0 с дополнительным ограничением коммерческого использования. Свободно для личного использования и некоммерческого распространения. Коммерческое использование — только с моего письменного разрешения: **tim.korelov@yandex.com**.

Полный текст — в [`LICENSE`](../LICENSE) (English). Краткое описание на русском — в [`LICENSE.ru.md`](../LICENSE.ru.md).
