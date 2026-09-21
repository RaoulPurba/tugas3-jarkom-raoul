import argparse
import socket
from pathlib import Path

from protocol import recv_json, send_frame, send_json

DEFAULT_SERVER = "127.0.0.1"
DEFAULT_PORT = 12000
CHUNK_SIZE = 64 * 1024


def send_text(sock: socket.socket, message: str):
    send_json(sock, {"type": "text", "message": message})
    response = recv_json(sock)
    print("[SERVER]", response.get("message"))


def send_file(sock: socket.socket, file_path: str):
    path = Path(file_path)

    if not path.is_file():
        print(f"[CLIENT] File tidak ditemukan: {path}")
        return

    size = path.stat().st_size

    send_json(
        sock,
        {
            "type": "file_start",
            "name": path.name,
            "size": size,
        },
    )

    with path.open("rb") as source:
        while True:
            chunk = source.read(CHUNK_SIZE)
            if not chunk:
                break
            send_frame(sock, chunk)

    response = recv_json(sock)
    print("[SERVER]", response.get("message"))


def run_client(server: str, port: int):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((server, port))

    print(f"[CLIENT] Terhubung ke TCP server {server}:{port}")
    print("Perintah:")
    print("  msg <teks>       kirim pesan")
    print("  file <path>      kirim file")
    print("  quit             keluar")

    try:
        while True:
            command = input("> ").strip()

            if not command:
                continue

            if command == "quit":
                send_json(client_socket, {"type": "quit"})
                response = recv_json(client_socket)
                print("[SERVER]", response.get("message"))
                break

            if command.startswith("msg "):
                send_text(client_socket, command[4:])
                continue

            if command.startswith("file "):
                send_file(client_socket, command[5:].strip())
                continue

            print("Perintah tidak dikenal. Gunakan msg, file, atau quit.")
    finally:
        client_socket.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TCP client")
    parser.add_argument("--server", default=DEFAULT_SERVER)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()

    run_client(args.server, args.port)
