import argparse
import json
import socket
import statistics
import time

DEFAULT_SERVER = "127.0.0.1"
DEFAULT_PORT = 12001
PING_COUNT = 10
TIMEOUT = 1.0
BUFFER_SIZE = 4096


def run_pinger(server: str, port: int, count: int, bind_port: int | None):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    if bind_port is not None:
        # Untuk eksperimen explicit bind local UDP port.
        client_socket.bind(("", bind_port))
        print(f"[UDP CLIENT] Explicit bind ke local port {bind_port}")

    # Timeout 1 detik sesuai spesifikasi tugas.
    client_socket.settimeout(TIMEOUT)

    rtts_ms = []
    received = 0

    print(
        f"[UDP CLIENT] Ping {server}:{port}, count={count}, "
        f"timeout={TIMEOUT:.1f}s"
    )

    try:
        for sequence in range(1, count + 1):
            payload = {
                "type": "ping",
                "seq": sequence,
                "client_send_time": time.time(),
            }

            data = json.dumps(payload).encode("utf-8")

            start = time.perf_counter()
            client_socket.sendto(data, (server, port))

            try:
                response, address = client_socket.recvfrom(BUFFER_SIZE)
                end = time.perf_counter()

                response_obj = json.loads(response.decode("utf-8"))

                # Pastikan reply sesuai dengan ping yang sedang diukur.
                if response_obj.get("seq") != sequence:
                    print(
                        f"Ping {sequence}: menerima seq yang tidak cocok "
                        f"({response_obj.get('seq')}), paket diabaikan."
                    )
                    continue

                rtt_ms = (end - start) * 1000.0
                rtts_ms.append(rtt_ms)
                received += 1

                print(
                    f"Ping {sequence}: reply dari "
                    f"{address[0]}:{address[1]} "
                    f"RTT={rtt_ms:.3f} ms"
                )

            except socket.timeout:
                print(
                    f"Ping {sequence}: "
                    f"Request timed out (> {TIMEOUT:.1f}s)"
                )

            except (json.JSONDecodeError, UnicodeDecodeError):
                print(
                    f"Ping {sequence}: "
                    "menerima response UDP yang tidak valid."
                )

    finally:
        client_socket.close()

    sent = count
    lost = sent - received
    loss_percentage = (lost / sent * 100.0) if sent else 0.0

    print("\n--- Statistik UDP Ping ---")
    print(f"Sent     : {sent}")
    print(f"Received : {received}")
    print(f"Lost     : {lost}")
    print(f"Loss     : {loss_percentage:.1f}%")

    if rtts_ms:
        print(f"RTT min  : {min(rtts_ms):.3f} ms")
        print(f"RTT avg  : {statistics.mean(rtts_ms):.3f} ms")
        print(f"RTT max  : {max(rtts_ms):.3f} ms")
    else:
        print("RTT      : tidak tersedia karena semua paket lost.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UDP pinger client")
    parser.add_argument("--server", default=DEFAULT_SERVER)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--count", type=int, default=PING_COUNT)
    parser.add_argument(
        "--bind-port",
        type=int,
        default=None,
        help="Optional explicit local UDP port, contoh: 5432.",
    )

    args = parser.parse_args()
    run_pinger(args.server, args.port, args.count, args.bind_port)
