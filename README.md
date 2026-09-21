# Hybrid Socket Programming — Python

Implementasi tugas **Pengembangan dan Analisis Sistem Distribusi Pesan & File Berbasis Hybrid Socket**.

## Arsitektur

- `TCPServer.py` — multi-threaded TCP server pada port `12000`
- `TCPClient.py` — client CLI untuk pesan teks dan file
- `UDPServer.py` — UDP heartbeat/echo server pada port `12001`
- `UDPClient.py` — UDP pinger 10 kali, timeout 1 detik, statistik RTT dan packet loss
- `protocol.py` — application-layer framing menggunakan 4-byte length header
- `ANALISIS.md` — jawaban Bagian A dan B

## Requirement

- Python 3.10+ direkomendasikan
- Tidak membutuhkan package eksternal

## Menjalankan server

Buka Terminal 1:

```bash
python TCPServer.py
```

Buka Terminal 2:

```bash
python UDPServer.py
```

## Menjalankan TCP client

Terminal 3:

```bash
python TCPClient.py
```

Contoh:

```text
> msg Halo server
> file contoh.pdf
> quit
```

Untuk menguji multi-client, buka beberapa terminal dan jalankan `TCPClient.py` secara bersamaan.

## Menjalankan UDP pinger

```bash
python UDPClient.py
```

Secara default client mengirim 10 ping dengan timeout 1 detik.

Eksperimen explicit bind local port 5432:

```bash
python UDPClient.py --bind-port 5432
```

Jika dua client pada host yang sama mencoba bind ke port UDP lokal yang sama, client kedua umumnya akan gagal dengan `Address already in use` karena tuple alamat lokal tersebut sudah terikat.

## Wireshark

Gunakan filter:

```text
tcp.port == 12000
```

untuk trafik TCP, dan:

```text
udp.port == 12001
```

untuk trafik UDP.

Bukti yang disarankan:

1. TCP three-way handshake.
2. Beberapa paket TCP saat pesan/file dikirim.
3. UDP request dan reply.
4. Jika ingin menunjukkan timeout/loss, hentikan sementara `UDPServer.py` ketika pinger berjalan atau lakukan pengujian pada jaringan yang memungkinkan packet loss.

## Framing TCP

TCP adalah byte-stream dan tidak menjaga batas pemanggilan `send()`. Karena itu proyek ini memakai:

```text
[4-byte payload length][payload]
```

Fungsi `send_frame()` dan `recv_frame()` memastikan receiver mengetahui berapa byte yang membentuk satu message/frame.

## Catatan File Transfer

File dikirim melalui TCP. Client mengirim metadata `file_start` terlebih dahulu, lalu isi file dikirim sebagai frame-frame binary sampai ukuran file terpenuhi. File diterima di folder:

```text
received_files/
```
