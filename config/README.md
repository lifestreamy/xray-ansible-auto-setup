# `config/`

Параметры для роли `xray_vpn`. Один файл — источник истины.

## Что внутри

- `settings.yml` — все параметры, которые нужны Ansible при развёртывании. Загружается из `deploy.yml` через `vars_files`. Раньше значения жили в двух местах (`group_vars/all.yml` и `roles/xray_vpn/defaults/main.yml`) — теперь они в одном файле.

## Почему так

Раньше часть переменных дублировалась между `group_vars/all.yml` и `roles/xray_vpn/defaults/main.yml`. Конфликт решался приоритетом Ansible (group_vars перекрывают role defaults), но это давало ошибки: правишь в одном месте, забываешь про второе — отладка на час.

Теперь все параметры в `settings.yml`. Роль не имеет собственных дефолтов; `group_vars/` удалён. Один файл, один источник.

## Что переопределять

Персональные значения под конкретный VPS (например, `num_clients` или `reality_camouflage_domain`) задаются в `inventory.yml` (создайте сами из `inventory.yml.example`; файл не коммитится, в `.gitignore`). Либо через CLI-флаги клиента `xrayvpn` — см. `docs/SETUP.md`.

Для локального тестирования через Ansible molecule значения лежат в `molecule/default/molecule.yml` — блок `provisioner.inventory.group_vars.all`.

## Примечания

- Предупреждение про инцидент 2026-07-28 рядом с `xray_docker_image` не удалять.