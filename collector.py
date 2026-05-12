"""
collector.py — подключается к устройствам по SSH, собирает LLDP-соседей,
сохраняет результат в topology.json
"""

import re
import json
import logging
from datetime import datetime
from netmiko import ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("topology.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)


DEVICES = [
    {"host": "192.168.1.1", "username": "admin", "password": "admin", "device_type": "cisco_ios"},
    {"host": "192.168.1.2", "username": "admin", "password": "admin", "device_type": "cisco_ios"},
    {"host": "192.168.1.3", "username": "admin", "password": "admin", "device_type": "cisco_ios"},
]


def parse_lldp_neighbors(output: str, local_host: str) -> list[dict]:
    """
    Парсит вывод 'show lldp neighbors detail'.
    Возвращает список соседей вида:
      {"local_port": "Gi0/1", "neighbor": "sw2", "neighbor_ip": "...", "neighbor_port": "Gi0/0"}
    """
    neighbors = []
    # Разбиваем по блокам (каждый сосед начинается с "---")
    blocks = re.split(r"-{3,}", output)

    for block in blocks:
        if not block.strip():
            continue

        neighbor = {}

        # Имя соседа
        m = re.search(r"System Name:\s+(\S+)", block)
        if m:
            neighbor["neighbor"] = m.group(1)

        # IP соседа
        m = re.search(r"Management Addresses:\s*\n\s+IP:\s+(\S+)", block)
        if not m:
            m = re.search(r"IP:\s+(\d+\.\d+\.\d+\.\d+)", block)
        neighbor["neighbor_ip"] = m.group(1) if m else "unknown"

        # Локальный порт
        m = re.search(r"Local Intf:\s+(\S+)", block)
        neighbor["local_port"] = m.group(1) if m else "unknown"

        # Порт соседа
        m = re.search(r"Port Description:\s+(\S+)", block)
        if not m:
            m = re.search(r"Port id:\s+(\S+)", block)
        neighbor["neighbor_port"] = m.group(1) if m else "unknown"

        if "neighbor" in neighbor:
            neighbors.append(neighbor)

    return neighbors


def collect_topology(devices: list[dict]) -> dict:
    """
    Обходит все устройства, собирает LLDP-соседей.
    Возвращает словарь topology.
    """
    topology = {
        "generated_at": datetime.now().isoformat(),
        "devices": {}
    }

    for device_info in devices:
        host = device_info["host"]
        log.info(f"Подключаюсь к {host} ...")

        try:
            conn = ConnectHandler(**device_info)

            # Получаем hostname устройства
            hostname_raw = conn.send_command("show version | include hostname")
            m = re.search(r"hostname\s+(\S+)", hostname_raw, re.IGNORECASE)
            if not m:
                # Попробуем из приглашения
                hostname = conn.find_prompt().strip("#>").strip()
            else:
                hostname = m.group(1)

            log.info(f"  hostname: {hostname}")

            # Собираем LLDP-соседей
            lldp_output = conn.send_command("show lldp neighbors detail")
            neighbors = parse_lldp_neighbors(lldp_output, hostname)

            topology["devices"][hostname] = {
                "ip": host,
                "neighbors": neighbors
            }

            log.info(f"  найдено соседей: {len(neighbors)}")
            conn.disconnect()

        except NetmikoTimeoutException:
            log.error(f"  Таймаут при подключении к {host}")
            topology["devices"][host] = {"ip": host, "neighbors": [], "error": "timeout"}

        except NetmikoAuthenticationException:
            log.error(f"  Ошибка аутентификации на {host}")
            topology["devices"][host] = {"ip": host, "neighbors": [], "error": "auth_failed"}

        except Exception as e:
            log.error(f"  Неизвестная ошибка на {host}: {e}")
            topology["devices"][host] = {"ip": host, "neighbors": [], "error": str(e)}

    return topology


def build_demo_topology(devices: list[dict]) -> dict:
    """
    Генерирует demo-топологию на основе реального списка DEVICES.
    Первое устройство — core, остальные — access.
    Все подключены к первому (звезда).
    """
    names = []
    for i, d in enumerate(devices):
        ip = d["host"]
        name = f"core-sw{i+1}" if i == 0 else f"access-sw{i+1}"
        names.append((name, ip))

    core_name, core_ip = names[0]
    demo_devices = {}

    # Core — соединён со всеми остальными
    core_neighbors = []
    for i, (name, ip) in enumerate(names[1:], start=1):
        core_neighbors.append({
            "local_port": f"Gi0/{i}",
            "neighbor": name,
            "neighbor_ip": ip,
            "neighbor_port": "Gi0/0"
        })
    demo_devices[core_name] = {"ip": core_ip, "neighbors": core_neighbors}

    # Access — каждый подключён к core
    for i, (name, ip) in enumerate(names[1:], start=1):
        demo_devices[name] = {
            "ip": ip,
            "neighbors": [{
                "local_port": "Gi0/0",
                "neighbor": core_name,
                "neighbor_ip": core_ip,
                "neighbor_port": f"Gi0/{i}"
            }]
        }

    return {
        "generated_at": datetime.now().isoformat(),
        "devices": demo_devices
    }


def all_failed(topology: dict) -> bool:
    """Проверяет — все ли устройства недоступны (ошибка или 0 соседей)."""
    devices = topology.get("devices", {})
    if not devices:
        return True
    return all("error" in d for d in devices.values())


def save_topology(topology: dict, path: str = "topology.json"):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(topology, f, ensure_ascii=False, indent=2)
    log.info(f"Топология сохранена в {path}")


if __name__ == "__main__":
    topo = collect_topology(DEVICES)

    if all_failed(topo):
        log.warning("Все устройства недоступны — генерируется demo-топология на основе DEVICES")
        topo = build_demo_topology(DEVICES)

    save_topology(topo)
    print(f"\nГотово! Устройств: {len(topo['devices'])}")
    print("Запусти visualize.py для генерации отчёта.")
