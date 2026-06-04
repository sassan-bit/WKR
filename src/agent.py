"""
Corporate Antivirus Agent — запускается на каждом клиентском ПК.
Следит за папкой, отправляет файл на центральный сканер для проверки.

Использование:
    python agent.py --server 192.168.3.2 --watch "C:/"
    python agent.py --server 192.168.3.2 --watch /mnt/shared
"""
import argparse
import json
import platform
import socket
import threading
import time
import uuid
from pathlib import Path

try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer
except ImportError:
    print("ERROR: watchdog не установлен. Выполните: pip install watchdog")
    raise SystemExit(1)

PE_EXT       = {".exe", ".dll", ".sys"}
DEFAULT_PORT = 45000
FILE_PORT    = 45001


def _get_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def _get_mac() -> str:
    mac = uuid.getnode()
    return ":".join(f"{(mac >> (8 * i)) & 0xFF:02X}" for i in range(5, -1, -1))


class AgentEventHandler(FileSystemEventHandler):
    def __init__(self, server_ip: str, server_port: int, watch_path: str):
        super().__init__()
        self._server_ip   = server_ip
        self._server_port = server_port
        self._udp_sock    = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._meta = {
            "hostname": platform.node(),
            "ip":       _get_ip(),
            "mac":      _get_mac(),
        }
        print(f"  Hostname : {self._meta['hostname']}")
        print(f"  IP       : {self._meta['ip']}")
        print(f"  MAC      : {self._meta['mac']}")
        print(f"  Watching : {watch_path}")
        print(f"  Scanner  → {server_ip}:{server_port} (UDP notify)")
        print(f"           → {server_ip}:{FILE_PORT} (TCP file transfer)")
        print()

    def on_created(self, event):
        if event.is_directory:
            return
        p = Path(event.src_path)
        if p.suffix.lower() not in PE_EXT:
            return
        time.sleep(0.3)  # ждём пока файл допишется
        threading.Thread(target=self._report, args=(p,), daemon=True).start()

    def _report(self, p: Path):
        # UDP уведомление
        payload = {
            **self._meta,
            "filepath":  str(p),
            "filename":  p.name,
            "event":     "file_created",
            "timestamp": time.time(),
        }
        try:
            self._udp_sock.sendto(
                json.dumps(payload).encode("utf-8"),
                (self._server_ip, self._server_port))
        except Exception:
            pass

        # TCP передача файла
        try:
            file_data = p.read_bytes()
        except Exception as ex:
            print(f"[!] Не удалось прочитать файл: {ex}")
            return

        header = json.dumps({
            **self._meta,
            "filename": p.name,
            "filesize": len(file_data),
        }).encode("utf-8")

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(15)
                s.connect((self._server_ip, FILE_PORT))
                s.sendall(len(header).to_bytes(4, "big"))
                s.sendall(header)
                s.sendall(file_data)
            print(f"[↑] Uploaded for scan: {p.name}")
        except Exception as ex:
            print(f"[!] Ошибка передачи: {ex}")


def main():
    parser = argparse.ArgumentParser(description="Corporate Antivirus Agent")
    parser.add_argument("--server", required=True,
                        help="IP сканера (например 192.168.3.2)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT,
                        help=f"UDP порт (по умолчанию: {DEFAULT_PORT})")
    parser.add_argument("--watch", required=True,
                        help="Папка для мониторинга (например C:/ или /mnt/shared)")
    args = parser.parse_args()

    watch = Path(args.watch)
    if not watch.exists():
        print(f"ERROR: Путь не существует: {watch}")
        raise SystemExit(1)

    print("=== Corporate Antivirus Agent ===")
    handler = AgentEventHandler(args.server, args.port, str(watch))

    observer = Observer()
    observer.schedule(handler, str(watch), recursive=True)
    observer.daemon = True
    observer.start()
    print("Агент запущен. Для остановки нажмите Ctrl+C.\n")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nОстановка агента...")
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()
