import argparse
import os
import socket
import threading
from pathlib import Path

from protocol import recv_frame, recv_json, send_json

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 12000
BUFFER_CHUNK = 64 * 1024


def safe_filename(name: str) -> str:
    """Prevent directory traversal; keep only the basename."""
    return os.path.basename(name) or "unnamed_file"


def handle_client(connection_socket: socket.socket, client_address, save_dir: Path):
    thread_name = threading.current_thread().name
    print(f"[TCP] {thread_name}: client terhubung {client_address}")

    try:
        while True:
            request = recv_json(connection_socket)
            request_type = request.get("type")

            if request_type == "text":
                message = str(request.get("message", ""))
                print(f"[TCP] {client_address} TEXT: {message}")

                send_json(
                    connection_socket,
                    {
                        "type": "ack",
                        "status": "ok",
                        "message": f"Pesan diterima server: {message}",
                    },
                )

            elif request_type == "file_start":
                filename = safe_filename(str(request.get("name", "unnamed_file")))
                filesize = int(request.get("size", 0))

                if filesize < 0:
                    raise ValueError("Ukuran file tidak valid.")

                target = save_dir / filename
                received = 0

                print(
                    f"[TCP] {client_address} FILE: {filename} "
                    f"({filesize} byte) -> {target}"
                )

                with target.open("wb") as output:
                    while received < filesize:
                        chunk = recv_frame(connection_socket)

                        # Menjaga agar client tidak mengirim lebih dari ukuran metadata.
                        remaining = filesize - received
                        if len(chunk) > remaining:
                            raise ValueError(
                                "Ukuran chunk melebihi sisa ukuran file yang diumumkan."
                            )

                        output.write(chunk)
                        received += len(chunk)

                send_json(
                    connection_socket,
                    {
                        "type": "ack",
                        "status": "ok",
                        "message": f"File {filename} diterima ({received} byte).",
                    },
                )

            elif request_type == "quit":
                send_json(
                    connection_socket,
                    {
                        "type": "ack",
                        "status": "bye",
                        "message": "Koneksi TCP ditutup oleh server.",
                    },
                )
                break

            else:
                send_json(
                    connection_socket,
                    {
                        "type": "error",
                        "status": "error",
                        "message": f"Tipe request tidak dikenal: {request_type}",
                    },
                )

    except (ConnectionError, ConnectionResetError, BrokenPipeError):
        print(f"[TCP] {client_address}: koneksi terputus.")
    except Exception as exc:
        print(f"[TCP] {client_address}: error: {exc}")
        try:
            send_json(
                connection_socket,
                {"type": "error", "status": "error", "message": str(exc)},
            )
        except Exception:
            pass
    finally:
        connection_socket.close()
        print(f"[TCP] {thread_name}: connection socket {client_address} ditutup.")


def run_server(host: str, port: int, save_dir: str):
    save_path = Path(save_dir)
    save_path.mkdir(parents=True, exist_ok=True)

    # Ini adalah welcoming socket / listening socket.
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, port))
    server_socket.listen()

    print(f"[TCP] Server listening di {host}:{port}")
    print(f"[TCP] File yang diterima disimpan di: {save_path.resolve()}")

    try:
        while True:
            # accept() membuat connection socket baru untuk satu client.
            connection_socket, client_address = server_socket.accept()

            worker = threading.Thread(
                target=handle_client,
                args=(connection_socket, client_address, save_path),
                daemon=True,
            )
            worker.start()

            print(
                f"[TCP] Thread baru: {worker.name}. "
                f"Active threads: {threading.active_count()}"
            )
    except KeyboardInterrupt:
        print("\n[TCP] Server dihentikan.")
    finally:
        # Welcoming socket hidup sepanjang server menerima client baru.
        server_socket.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-threaded TCP server")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--save-dir", default="received_files")
    args = parser.parse_args()

    run_server(args.host, args.port, args.save_dir)
