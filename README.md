# Проект 3 — Построение топологии сети (LLDP)

## Описание

Скрипт автоматически подключается к сетевым устройствам по SSH, собирает данные о соседях через протокол LLDP и строит интерактивную карту топологии сети в виде HTML-дашборда.

**Как это работает:**

```
collector.py  →  topology.json  →  visualize.py  →  topology_report.html
```

1. `collector.py` подключается к каждому устройству по SSH и выполняет команду `show lldp neighbors detail`
2. Парсит вывод и сохраняет данные о связях в `topology.json`
3. `visualize.py` читает `topology.json` и генерирует интерактивный граф

---

## Структура проекта

```
project/
├── collector.py          # Сбор данных с устройств по SSH
├── visualize.py          # Генерация HTML-отчёта
├── requirements.txt      # Зависимости Python
├── topology.json         # Результат сбора (создаётся автоматически)
├── topology_report.html  # Итоговый отчёт (создаётся автоматически)
└── topology.log          # Лог подключений (создаётся автоматически)
```

---

## Установка

```bash
py -m pip install -r requirements.txt
```

---

## Настройка

Открой `collector.py` и укажи свои устройства в списке `DEVICES`:

```python
DEVICES = [
    {"host": "192.168.1.1", "username": "admin", "password": "admin", "device_type": "cisco_ios"},
    {"host": "192.168.1.2", "username": "admin", "password": "admin", "device_type": "cisco_ios"},
    {"host": "192.168.1.3", "username": "admin", "password": "admin", "device_type": "cisco_ios"},
]
```

| Параметр      | Описание                              |
|---------------|---------------------------------------|
| `host`        | IP-адрес устройства                   |
| `username`    | Логин SSH                             |
| `password`    | Пароль SSH                            |
| `device_type` | Тип устройства (см. таблицу ниже)    |

**Поддерживаемые типы устройств:**

| `device_type`     | Вендор            |
|-------------------|-------------------|
| `cisco_ios`       | Cisco IOS         |
| `cisco_xe`        | Cisco IOS-XE      |
| `cisco_nxos`      | Cisco NX-OS       |
| `juniper_junos`   | Juniper JunOS     |
| `huawei`          | Huawei VRP        |

---

## Запуск

**Шаг 1 — собери топологию:**

```bash
& C:/Users/.../python.exe collector.py
```

Скрипт подключится к каждому устройству и сохранит результат в `topology.json`.

> Если все устройства недоступны — скрипт автоматически генерирует demo-топологию на основе списка `DEVICES`.

**Шаг 2 — сгенерируй отчёт:**

```bash
& C:/Users/.../python.exe visualize.py
```

Открой `topology_report.html` в браузере — увидишь интерактивную карту сети.

---

## Пример topology.json

```json
{
  "generated_at": "2026-05-12T10:00:00",
  "devices": {
    "core-sw1": {
      "ip": "192.168.1.1",
      "neighbors": [
        {
          "local_port": "Gi0/1",
          "neighbor": "access-sw2",
          "neighbor_ip": "192.168.1.2",
          "neighbor_port": "Gi0/0"
        }
      ]
    }
  }
}
```

---

## Визуализация

Интерактивный HTML-дашборд показывает:

- Граф сети — узлы можно перетаскивать мышкой
- Цвет узла по типу устройства:
  - Синий — Core / Distribution switch
  - Фиолетовый — Access switch
  - Зелёный — Router
- Подписи портов на каждой связи (`Gi0/1 ↔ Gi0/0`)
- Клик на узел — подробности (IP, тип, список соседей)
- Подсветка всех связей выбранного устройства
- Кнопки зума `+` / `−` / сброс

---

## Лог

Все события пишутся в `topology.log`:

```
2026-05-12 10:00:01 [INFO]    Подключаюсь к 192.168.1.1 ...
2026-05-12 10:00:03 [INFO]    hostname: core-sw1
2026-05-12 10:00:04 [INFO]    найдено соседей: 2
2026-05-12 10:00:04 [INFO]    Топология сохранена в topology.json
```

---

## Зависимости

| Библиотека | Назначение                     |
|------------|-------------------------------|
| `netmiko`  | SSH-подключение к устройствам |
| `d3.js`    | Визуализация графа (CDN)      |
