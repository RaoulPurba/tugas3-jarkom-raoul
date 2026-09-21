import argparse
import socket

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 12001
BUFFER_SIZE = 4096


def run_server(host: str, port: int):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((host, port))

    print(f"[UDP] Heartbeat server listening di {host}:{port}")

    try:
        while True:
            data, client_address = server_socket.recvfrom(BUFFER_SIZE)

            # UDP mempertahankan message boundary:
            # satu recvfrom() menerima satu datagram (jika buffer mencukupi).
            print(
                f"[UDP] Datagram {len(data)} byte dari "
                f"{client_address[0]}:{client_address[1]}"
            )

            # Echo kembali paket yang sama untuk pengukuran RTT.
            server_socket.sendto(data, client_address)

    except KeyboardInterrupt:
        print("\n[UDP] Server dihentikan.")
    finally:
        server_socket.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UDP heartbeat/echo server")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()

    run_server(args.host, args.port)
