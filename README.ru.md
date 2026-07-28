# Развёртывание Xray Reality VPN-сервера

[English](README.md) | [Русский](README.ru.md)

**Полностью автоматизированная Ansible-настройка для установки Xray Reality VPN-сервера на удалённый VPS.**

> Генерирует клиентские конфигурации для Clash Verge / FlClash (Mihomo Meta YAML) и Amnezia VPN (JSON). Clash Verge и FlClash являются рекомендуемыми клиентами; Amnezia — вторичный вариант с известными ограничениями (см. [Расширенная конфигурация](#расширенная-конфигурация)).

## Где запускается
- Linux
  - Через bash-обёртку
  - Или командой `ansible-playbook` (самостоятельное скачивание клиентских конфигураций на вашей машине)
- Windows — PowerShell-обёртка + WSL

---

## Что делает эта настройка

- Настраивает свежий Ubuntu/Debian VPS с Xray-core VPN-сервером и протоколом VLESS с транспортом Reality (режим стелс)
- Автоматически генерирует и экспортирует клиентские конфигурации: Clash Meta YAML (`.yaml`) для Clash Verge/FlClash + JSON (`.json`) для Amnezia VPN
- После завершения откатывает только те изменения, которые внёс

## Требования

**Локальная машина:**

*Linux:*
- Ubuntu/Debian (или любой дистрибутив с `apt`)
- SSH-доступ к целевому VPS

*Windows:*
- WSL2 с Ubuntu/Debian (должен быть предустановлен)
- PowerShell 5.1+ (встроен в Windows 10/11)

**VPS:**
- Свежая установка Ubuntu 20.04+ или Debian 11+
- Root или sudo доступ
- Публичный IP-адрес

> **Примечание:** Скрипт автоматически устанавливает необходимые зависимости (Python 3, Ansible, sshpass) на вашей локальной машине. На Windows требуется только WSL.

## Быстрый старт

**В минимальном случае вам нужны только IP-адрес VPS и пароль, всё остальное делает скрипт.**

Скрипты-обёртки позволяют легко запускать настройку как из Windows, так и из Linux.

### Linux/WSL (Bash)

Полную справку по CLI можно получить: `./provision-vpn.sh -h`

```bash
# Режим CLI (передача параметров напрямую) 
./provision-vpn.sh -H 1.2.3.4 --pkey ~/.ssh/id_rsa

# Режим CLI (только хост, пароль будет скрыто запрошен интерактивно) 
./provision-vpn.sh -H 1.2.3.4

# Режим inventory (использовать предзаполненный inventory.yml)
./provision-vpn.sh --use-inventory
```

### Windows (PowerShell)

Полную справку по CLI можно получить: `Get-Help .\Provision-VPN.ps1 -Full`

```powershell
# Режим CLI
.\Provision-VPN.ps1 -HostName 1.2.3.4 -PKey C:\Users\You\.ssh\id_rsa

# Режим CLI (только хост, пароль будет скрыто запрошен интерактивно) 
.\Provision-VPN.ps1 -HostName 1.2.3.4

# Режим inventory
.\Provision-VPN.ps1 -UseInventory
```

## Конфигурация

### Вариант 1: CLI-параметры

> Поддерживает SSH-ключ, парольную аутентификацию или интерактивный ввод пароля (скрытый)

Передайте параметры подключения через флаги командной строки:

```bash
./provision-vpn.sh -H <VPS_IP> -u <SSH_USER> -p <SSH_PORT> --pkey <PATH_TO_KEY>
```

### Вариант 2: Inventory-файл

Отредактируйте `inventory.yml` с данными вашего VPS и используйте флаг `--use-inventory`:

```yaml
all:
  hosts:
    your_host:
      ansible_host: 1.2.3.4
      ansible_user: root
      ansible_port: 22
      ansible_ssh_private_key_file: /path/to/key
      ansible_ssh_pass: (оставьте пустым или используйте вместо pkey; pkey в приоритете)
```

## Параметры

### Bash-скрипт

| Флаг | Описание | Обязательно |
|------|----------|-------------|
| `-H, --host` | IP/хост VPS | Да (режим CLI) |
| `-u, --user` | SSH-пользователь | Нет (по умолчанию: root) |
| `-p, --port` | SSH-порт | Нет (по умолчанию: 22) |
| `--pkey` | Путь к приватному SSH-ключу | Нет* |
| `--pass` | SSH-пароль | Нет* |
| `--use-inventory` | Использовать inventory.yml вместо CLI-аргументов | Нет |
| `--clients-dir` | Папка для клиентских конфигов | Нет |
| `--cleanup` | Удалить временную рабочую папку (по умолчанию) | Нет |
| `--full-cleanup` | Удалить рабочую папку и установленные пакеты | Нет |
| `--no-cleanup` | Сохранить рабочую папку для отладки | Нет |
| `--dry-run` | Показать команды без выполнения | Нет |

*Необходимо указать `--pkey` или `--pass`; если ни один не указан — будет интерактивный скрытый ввод пароля.

### PowerShell-скрипт

Те же параметры с PowerShell-именами:
- `-HostName` вместо `--host`
- `-PKey` вместо `--pkey`
- `-Pass` вместо `--pass`
- `-UseInventory` вместо `--use-inventory`
- `-CleanupMode` (`Default`, `Full`, `None`)
- `-LogLevel` (`None`, `Default`, `Verbose`)

## Результат

Клиентские конфигурационные файлы сохраняются на вашей локальной машине:
- Linux: `./downloaded-clients/*.json` и `./downloaded-clients/*.yaml`
- Windows: `.\downloaded-clients\*.json` и `.\downloaded-clients\*.yaml`

А также на целевом VPS:
- `/root/vpn-configs/*.json` (Amnezia) и `/root/vpn-configs/*.yaml` (Clash Verge / FlClash)

**Рекомендуемый путь:** импортируйте `clash_client_*.yaml` в Clash Verge (Windows/macOS/Linux, режим TUN) или FlClash (Android).  
**Вторичный вариант** (с оговорками): Amnezia `client_*.json` доступен, но имеет известные проблемы стабильности — Windows split-tunnel может обрушить сетевой стек; Android keepalive / фоновая работа ненадёжны. Используйте Clash Verge или FlClash, если вам не требуется именно Amnezia.  
Ссылки:  
- Clash Verge: https://github.com/clash-verge-rev/clash-verge-rev  
- FlClash: https://github.com/chen08209/FlClash  
- Amnezia: https://github.com/amnezia-vpn/amnezia-client

## Расширенная конфигурация

Для детального контроля над развёртыванием отредактируйте `group_vars/all.yml`:

```yaml
num_clients: 3                        # Количество генерируемых VPN-профилей
reality_camouflage_domain: dl.google.com  # Домен для REALITY-обфускации трафика
```

- `num_clients`: Количество создаваемых клиентских конфигураций (каждая с уникальным UUID)
> Даже одного конфигурационного файла достаточно для неограниченного числа одновременных подключений, но несколько профилей рекомендуются для раздачи другим людям и гранулярного контроля.
- `reality_camouflage_domain`: Легитимный домен, на который REALITY перенаправляет подозрительные соединения, делая VPN-трафик неотличимым от обычного HTTPS

Эти настройки передаются в Ansible playbook при развёртывании.

## Закреплённый образ и WARP IPv4

**Docker-образ Xray закреплён** на `teddysun/xray:26.6.27` (проверенная версия).  
`:latest` намеренно **не используется** в production-юнитах — автообновление до версии 26.7.11 в июле 2026 сломало совместимость VLESS+REALITY.  
Для осознанного обновления: измените `xray_docker_image` в `group_vars/all.yml` (тег или digest `sha256:…`), протестируйте, затем разверните.

**WARP outbound по умолчанию настроен на IPv4-only** для совместимости с VPS без IPv6-маршрута.  
- `warp_ipv6: false` — IPv6 WireGuard-адреса исключаются из конфигурации Xray.  
- `warp_endpoint: "162.159.192.1:2408"` — Cloudflare WARP IPv4 anycast (стабильное имя: `engage.cloudflareclient.com:2408`). При необходимости переопределите в `group_vars/all.yml`.  
- WARP включается через `warp_enabled: true` (требуется `wgcf` 2.2.22, скачивается автоматически).  
- Outbound `warp` является маршрутом по умолчанию для всего трафика при включении; `direct` — запасной.

**Ротация секретов** описана в [docs/SECRET_ROTATION.md](docs/SECRET_ROTATION.md).

## Дополнительные примеры

**Нестандартный SSH-порт и папка для конфигов:**
```bash
./provision-vpn.sh -H vps.example.com -p 2222 \
  --pkey ~/.ssh/id_rsa --clients-dir ~/vpn-configs
```

**Сухой прогон (тест без выполнения):**
```bash
./provision-vpn.sh -H 1.2.3.4 --pkey ~/.ssh/id_rsa --dry-run
```

**Полная очистка (удаление установленных пакетов после прогона):**
```bash
./provision-vpn.sh -H 1.2.3.4 --pkey ~/.ssh/id_rsa --full-cleanup
```

## Устранение неполадок

**"Command not found: ansible"**
- Скрипт должен установить ansible автоматически. Если не получилось, выполните вручную:
```bash
sudo apt-get update && sudo apt-get install -y ansible
```

**"Permission denied (publickey)"**
- Проверьте права SSH-ключа: `chmod 600 ~/.ssh/id_rsa`
- Проверьте SSH вручную: `ssh -i ~/.ssh/id_rsa user@host`

**"inventory.yml missing required fields"**
- Используйте `--use-inventory` только после заполнения всех полей в `inventory.yml`
- Или используйте CLI-режим с флагами `-H`, `--pkey`/`--pass`

**Проблемы с переносами строк (LF vs CRLF)**
- Скрипты форсируют LF через `.gitattributes`, поэтому проблем быть не должно
- Если проблемы сохраняются: `dos2unix provision-vpn.sh`, переклонируйте репозиторий или создайте issue на GitHub

## Участие в проекте

Вклад приветствуется. Пожалуйста, соблюдайте conventional commits, тестируйте с `--dry-run` и реальным запуском на вашем собственном VPS (включая проверку подключения через клиенты) перед отправкой изменений.

## Issues

Нашли баг? Пожалуйста, откройте issue с:
- Вашей настройкой (Linux/Windows, версия bash/PowerShell)
- Ожидаемое vs фактическое поведение
- Шаги для воспроизведения
- Релевантные логи из вывода

Есть предложение? Пожалуйста, откройте issue с:
- Как вы сейчас используете проект
- Что хотели бы добавить
- Если вы готовы предоставить и протестировать эту функциональность сами

## Лицензия

MIT

## Автор

Tim Korelov  
https://github.com/lifestreamy
