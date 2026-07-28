# Развёртывание Xray Reality VPN-сервера

[English](README.md) | [Русский](README.ru.md)

**Полностью автоматизированная Ansible-настройка для установки Xray Reality VPN-сервера на удалённый VPS.**

> Генерирует клиентские конфигурации для Clash Verge / FlClash (Mihomo Meta YAML) и Amnezia VPN (JSON). Clash Verge и FlClash являются рекомендуемыми клиентами; Amnezia — вторичный вариант с известными ограничениями.

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

### Linux/WSL (Bash)

```bash
# Режим CLI (передача параметров напрямую) 
./provision-vpn.sh -H 1.2.3.4 --pkey ~/.ssh/id_rsa

# Режим CLI (только хост, пароль будет скрыто запрошен интерактивно) 
./provision-vpn.sh -H 1.2.3.4

# Режим inventory (использовать предзаполненный inventory.yml)
./provision-vpn.sh --use-inventory
```

### Windows (PowerShell)

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
**Вторичный вариант:** Amnezia `client_*.json` доступен, но имеет известные проблемы стабильности — Windows split-tunnel может обрушить сетевой стек; Android keepalive / фоновая работа ненадёжны. Используйте Clash Verge или FlClash, если вам не требуется именно Amnezia.  
Ссылки:  
- Clash Verge: [https://github.com/clash-verge-rev/clash-verge-rev](https://github.com/clash-verge-rev/clash-verge-rev)  
- FlClash: [https://github.com/chen08209/FlClash](https://github.com/chen08209/FlClash)  
- Amnezia: [https://github.com/amnezia-vpn/amnezia-client](https://github.com/amnezia-vpn/amnezia-client)

## Расширенная конфигурация

Отредактируйте `group_vars/all.yml` для детального контроля:

```yaml
num_clients: 3                        # Количество генерируемых VPN-профилей
reality_camouflage_domain: dl.google.com  # Домен для REALITY-обфускации трафика
```

- `num_clients`: Количество создаваемых клиентских конфигураций (каждая с уникальным UUID)
- `reality_camouflage_domain`: Легитимный домен, на который REALITY перенаправляет подозрительные соединения

Эти настройки передаются в Ansible playbook при развёртывании.

## Закреплённый образ и WARP IPv4

**Docker-образ Xray закреплён** на `teddysun/xray:26.6.27` (проверенная версия).  
`:latest` намеренно **не используется** — автообновление до 26.7.11 в июле 2026 сломало совместимость VLESS+REALITY.  
Для осознанного обновления: измените `xray_docker_image` в `group_vars/all.yml`, протестируйте, затем разверните.

**WARP outbound настроен на IPv4-only** для совместимости с VPS без IPv6-маршрута.  
- `warp_ipv6: false` — IPv6 WireGuard-адреса исключаются из конфигурации Xray.  
- `warp_endpoint: "162.159.192.1:2408"` — Cloudflare WARP IPv4 anycast.  
- WARP включается через `warp_enabled: true` (требуется `wgcf` 2.2.22, скачивается автоматически).  
- Outbound `warp` является маршрутом по умолчанию для всего трафика при включении; `direct` — запасной.

## Персистентная идентичность

REALITY-ключи, short ID и клиентские UUID сохраняются в `/root/xray-config/reality-state.json`.  
Обычные повторные запуски сохраняют существующую идентичность — клиентские конфиги остаются стабильными.  
Для ротации всех учётных данных: установите `xray_reality_rotate: true` в `group_vars/all.yml` (или `-e xray_reality_rotate=true`).  
Старое состояние архивируется с меткой времени перед ротацией.

## Безопасность

- Чувствительные файлы (`config.json`, `reality-state.json`, WARP-профили) имеют режим `0600` (только root).
- Клиентские конфиги (`/root/vpn-configs/`) имеют режим `0640`.
- Приватные ключи не выводятся в логи Ansible.

## Дымовые проверки

Пост-деплой проверки: контейнер использует закреплённый образ, порт слушает, journal не содержит очевидных ошибок.  
Эти проверки НЕ верифицируют WARP-маршрутизацию — для этого подключитесь реальным VLESS-клиентом.

**Ротация секретов** описана в [docs/SECRET_ROTATION.md](docs/SECRET_ROTATION.md).

## Дополнительные примеры

```bash
# Нестандартный SSH-порт и папка для конфигов
./provision-vpn.sh -H vps.example.com -p 2222 --pkey ~/.ssh/id_rsa --clients-dir ~/vpn-configs

# Сухой прогон (тест без выполнения)
./provision-vpn.sh -H 1.2.3.4 --pkey ~/.ssh/id_rsa --dry-run

# Полная очистка
./provision-vpn.sh -H 1.2.3.4 --pkey ~/.ssh/id_rsa --full-cleanup
```

## Устранение неполадок

**"Command not found: ansible"**
- Скрипт должен установить ansible автоматически. Если нет:
```bash
sudo apt-get update && sudo apt-get install -y ansible
```

**"Permission denied (publickey)"**
- Проверьте права ключа: `chmod 600 ~/.ssh/id_rsa`

**"inventory.yml missing required fields"**
- Используйте `--use-inventory` только после заполнения всех полей

**Проблемы с переносами строк (LF vs CRLF)**
- `dos2unix provision-vpn.sh` или переклонируйте репозиторий

## Участие в проекте

Вклад приветствуется. Соблюдайте conventional commits, тестируйте с `--dry-run` и на собственном VPS перед отправкой изменений.

## Issues

Ошибка? Откройте issue с: настройкой, ожидаемым/фактическим поведением, шагами воспроизведения, логами.

Предложение? Откройте issue с: как используете, что добавить, готовы ли протестировать.

## Лицензия

MIT

## Автор

Tim Korelov  
[https://github.com/lifestreamy](https://github.com/lifestreamy)