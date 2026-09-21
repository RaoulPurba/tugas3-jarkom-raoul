# LAPORAN TUGAS SOCKET PROGRAMMING

## Pengembangan dan Analisis Sistem Distribusi Pesan & File Berbasis Hybrid Socket

**Mata Kuliah:** Jaringan Komputer Lanjut  
**Program Studi:** S2 Ilmu Komputer  
**Bahasa Pemrograman:** Python 3  
**Nama:** Raoul Purba  
**NIM:** 25/574540/PPA/07250  
**Tanggal:** 22 September 2026  

---

# 1. Pendahuluan

## 1.1 Latar Belakang

Socket programming merupakan mekanisme komunikasi antarproses melalui jaringan dengan memanfaatkan protokol transport seperti TCP dan UDP. TCP menyediakan komunikasi yang reliabel, berurutan, dan berbasis koneksi, sedangkan UDP bersifat connectionless dan tidak menjamin pengiriman paket.

Pada tugas ini dikembangkan sebuah aplikasi hybrid socket menggunakan Python 3 yang menggabungkan dua layanan utama:

1. **TCP multi-client** untuk pengiriman pesan teks dan file.
2. **UDP heartbeat/pinger** untuk mengukur Round Trip Time (RTT) dan packet loss.

Server TCP dirancang menggunakan mekanisme multithreading sehingga dapat melayani beberapa client secara bersamaan. Karena TCP merupakan byte-stream tanpa message boundary, aplikasi juga mengimplementasikan application-layer framing menggunakan header panjang data.

Sementara itu, layanan UDP digunakan sebagai heartbeat server. Client mengirimkan 10 paket ping dan menunggu balasan dengan timeout sebesar 1 detik. Hasil komunikasi TCP dan UDP kemudian diamati menggunakan Wireshark.

---

# 2. Tujuan

Tujuan dari tugas ini adalah:

1. Mengimplementasikan server TCP yang dapat menangani beberapa client secara bersamaan.
2. Memahami perbedaan welcoming socket dan connection socket.
3. Mengimplementasikan application-layer framing pada TCP.
4. Mengimplementasikan UDP heartbeat/pinger.
5. Menghitung RTT dan packet loss dari komunikasi UDP.
6. Menganalisis perbedaan karakteristik TCP dan UDP.
7. Mengamati paket TCP dan UDP menggunakan Wireshark.
8. Menganalisis penggunaan explicit bind pada UDP client.

---

# 3. Arsitektur Sistem

Sistem terdiri dari empat komponen utama:

```text
+------------------+                 +------------------+
|    TCP Client    | ---- TCP ----> |    TCP Server    |
|   TCPClient.py   |   Port 12000   |   TCPServer.py   |
+------------------+                 +------------------+
        |                                     |
        | Pesan teks / File                   |
        |                                     |
        +-------------------------------------+

+------------------+                 +------------------+
|    UDP Client    | ---- UDP ----> |    UDP Server    |
|   UDPClient.py   |   Port 12001   |   UDPServer.py   |
+------------------+                 +------------------+
        |                                     |
        | Ping / Heartbeat                    |
        | <------------- Echo ----------------+
```

File utama yang digunakan adalah:

```text
TCPServer.py
TCPClient.py
UDPServer.py
UDPClient.py
protocol.py
```

`protocol.py` digunakan untuk menangani framing pada komunikasi TCP.

---

# 4. Implementasi TCP Multi-Client

## 4.1 Welcoming Socket

Server TCP membuat satu socket utama sebagai welcoming socket:

```python
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((host, port))
server_socket.listen()
```

Welcoming socket bertugas menunggu permintaan koneksi dari client.

Server kemudian menjalankan:

```python
connection_socket, client_address = server_socket.accept()
```

Setiap pemanggilan `accept()` menghasilkan sebuah **connection socket** baru.

Welcoming socket tetap aktif selama server berjalan, sedangkan connection socket hanya digunakan untuk melayani satu client tertentu.

---

## 4.2 Multithreading

Agar server dapat menangani beberapa client secara bersamaan, setiap connection socket diproses menggunakan thread terpisah.

Contoh:

```python
worker = threading.Thread(
    target=handle_client,
    args=(connection_socket, client_address, save_path),
    daemon=True,
)

worker.start()
```

Dengan pendekatan tersebut, apabila satu client sedang melakukan transfer file atau menunggu operasi tertentu, client lain tetap dapat dilayani oleh server.

Apabila terdapat `N` client aktif, maka secara konseptual server TCP menggunakan:

```text
1 welcoming socket + N connection socket
```

Sehingga jumlah socket yang digunakan adalah:

```text
N + 1
```

---

# 5. Application-Layer Framing pada TCP

TCP menggunakan model **byte stream**. TCP tidak mempertahankan batas pesan berdasarkan pemanggilan `send()` dari aplikasi.

Misalnya client melakukan:

```python
sock.send(b"SATU")
sock.send(b"DUA")
sock.send(b"TIGA")
```

Server tidak selalu menerima data sebagai:

```text
SATU
DUA
TIGA
```

Data dapat diterima sebagai:

```text
SATUDUATIGA
```

atau bahkan terpecah menjadi beberapa bagian.

Untuk mengatasi permasalahan tersebut, aplikasi menggunakan **length-prefix framing**.

Format frame:

```text
+----------------------+-------------------------+
| 4-byte length header | Payload sepanjang N byte|
+----------------------+-------------------------+
```

Pengirim terlebih dahulu mengirimkan panjang payload dalam header 4 byte.

Contoh implementasi:

```python
header = struct.pack("!I", len(payload))
sock.sendall(header + payload)
```

Receiver membaca 4 byte pertama untuk mengetahui panjang payload, lalu membaca data sampai panjang tersebut terpenuhi.

Dengan demikian, aplikasi dapat menentukan batas setiap pesan secara independen dari segmentasi TCP.

---

# 6. Implementasi Transfer Pesan dan File

TCP digunakan untuk mengirim dua jenis data:

1. Pesan teks.
2. File.

Contoh perintah pada client:

```text
msg Halo Server
```

Untuk pengiriman file:

```text
file contoh.txt
```

Sebelum file dikirim, client mengirim metadata:

```json
{
  "type": "file_start",
  "name": "contoh.txt",
  "size": 1024
}
```

Selanjutnya isi file dikirim dalam beberapa frame sampai seluruh ukuran file terpenuhi.

TCP dipilih karena menyediakan:

- Reliable delivery.
- Ordered delivery.
- Error detection dan retransmission.
- Connection-oriented communication.

Karakteristik tersebut sesuai untuk transfer file karena kehilangan sebagian data dapat menyebabkan file rusak.

---

# 7. Implementasi UDP Heartbeat / Pinger

UDP server dijalankan pada port:

```text
12001
```

Server menggunakan satu UDP socket:

```python
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.bind((host, port))
```

Server menerima paket menggunakan:

```python
data, client_address = server_socket.recvfrom(BUFFER_SIZE)
```

Kemudian server mengembalikan paket tersebut ke client:

```python
server_socket.sendto(data, client_address)
```

Dengan demikian server bertindak sebagai UDP echo/heartbeat server.

---

## 7.1 Timeout

UDP tidak menjamin paket sampai ke tujuan. Karena itu client menerapkan timeout:

```python
client_socket.settimeout(1.0)
```

Apabila server tidak memberikan respons dalam waktu satu detik, paket dianggap mengalami timeout atau packet loss.

Contoh:

```python
try:
    response, address = client_socket.recvfrom(BUFFER_SIZE)

except socket.timeout:
    print("Request timed out")
```

---

## 7.2 Perhitungan RTT

RTT dihitung dari selisih waktu antara pengiriman request dan penerimaan response.

```python
start = time.perf_counter()

client_socket.sendto(data, (server, port))

response, address = client_socket.recvfrom(BUFFER_SIZE)

end = time.perf_counter()

rtt_ms = (end - start) * 1000
```

Pengujian dilakukan sebanyak:

```text
10 kali ping
```

Kemudian dihitung:

- RTT minimum.
- RTT rata-rata.
- RTT maksimum.
- Jumlah paket terkirim.
- Jumlah paket diterima.
- Jumlah packet loss.

Rumus packet loss:

```text
Packet Loss (%) =
(Jumlah Paket Hilang / Jumlah Paket Dikirim) × 100%
```

---

# 8. Pengujian Menggunakan Wireshark

Pengujian dilakukan menggunakan Wireshark untuk mengamati paket TCP dan UDP secara langsung.

Karena client dan server dijalankan pada komputer yang sama menggunakan alamat:

```text
127.0.0.1
```

capture dilakukan menggunakan interface:

```text
Npcap Loopback Adapter
```

atau:

```text
Adapter for loopback traffic capture
```

---

# 9. Capture Komunikasi TCP

## 9.1 Menjalankan Program

Server dijalankan terlebih dahulu:

```powershell
python TCPServer.py
```

Kemudian client dijalankan pada terminal berbeda:

```powershell
python TCPClient.py
```

Contoh komunikasi:

```text
> msg Halo Server
> msg Percobaan TCP Jaringan Komputer
> file contoh.txt
> quit
```

---

## 9.2 Filter Wireshark TCP

Display filter yang digunakan:

```text
tcp.port == 12000
```

Filter tersebut hanya menampilkan komunikasi TCP yang menggunakan port server 12000.

---

## 9.3 TCP Three-Way Handshake

Saat client pertama kali terhubung ke server, Wireshark memperlihatkan proses:

```text
Client                    Server

  | -------- SYN --------> |
  | <---- SYN, ACK --------|
  | -------- ACK --------> |
```

Proses tersebut disebut **TCP Three-Way Handshake**.

Three-way handshake digunakan untuk membentuk koneksi TCP sebelum aplikasi mulai mengirimkan data.

### Bukti Wireshark

> **Sisipkan screenshot Wireshark TCP Three-Way Handshake di sini.**

Contoh penamaan file:

```text
images/tcp_handshake.png
```

Markdown:

```md
![TCP Three-Way Handshake](images/tcp_handshake.png)
```

### Analisis

Pada capture terlihat paket dengan flag:

```text
SYN
SYN, ACK
ACK
```

Hal ini menunjukkan bahwa TCP bersifat **connection-oriented**, sehingga client dan server harus membentuk koneksi sebelum melakukan pertukaran data.

---

# 10. Capture Transfer Data TCP

Setelah koneksi terbentuk, client mengirimkan pesan:

```text
msg Halo Server
```

Pada Wireshark akan muncul paket data TCP yang umumnya memiliki flag:

```text
PSH, ACK
```

### Bukti Wireshark

> **Sisipkan screenshot paket TCP yang membawa application data di sini.**

```md
![TCP Data Transfer](images/tcp_data.png)
```

### Analisis

Paket tersebut membawa data dari application layer. Pada implementasi ini payload terdiri dari:

```text
4-byte length header + JSON/application payload
```

TCP tidak mempertahankan message boundary. Karena itu satu pesan aplikasi tidak selalu identik dengan satu paket TCP yang terlihat di Wireshark.

Segmentasi data ditentukan oleh TCP dan sistem operasi.

Hal inilah yang menjadi alasan framing dilakukan pada application layer.

---

# 11. Capture Komunikasi UDP

UDP server dijalankan menggunakan:

```powershell
python UDPServer.py
```

Kemudian client dijalankan:

```powershell
python UDPClient.py
```

Client mengirimkan 10 paket ping.

---

## 11.1 Filter Wireshark UDP

Display filter yang digunakan:

```text
udp.port == 12001
```

Karena terdapat 10 request dan masing-masing mendapat satu response, pada kondisi tanpa packet loss Wireshark dapat memperlihatkan sekitar:

```text
10 request + 10 response = 20 datagram UDP
```

---

## 11.2 Request dan Response UDP

Contoh komunikasi:

```text
Client                        Server

Ephemeral Port  ----->       12001
Ephemeral Port  <-----       12001
```

Misalnya port client yang dipilih sistem operasi adalah:

```text
53214
```

maka request:

```text
Source Port      : 53214
Destination Port : 12001
```

Sedangkan response:

```text
Source Port      : 12001
Destination Port : 53214
```

### Bukti Wireshark

> **Sisipkan screenshot UDP request-response di sini.**

```md
![UDP Heartbeat](images/udp_heartbeat.png)
```

### Analisis

Tidak terdapat SYN, SYN-ACK, maupun ACK sebelum paket UDP dikirim.

Hal ini menunjukkan bahwa UDP bersifat:

```text
Connectionless
```

Server tidak membuat socket baru untuk setiap client. Satu UDP socket dapat menerima paket dari banyak client.

Alamat client diperoleh dari:

```python
data, client_address = server_socket.recvfrom(...)
```

dan response dikirim menggunakan:

```python
server_socket.sendto(data, client_address)
```

---

# 12. Message Boundary pada UDP

Berbeda dengan TCP, UDP mempertahankan batas datagram.

Satu pemanggilan:

```python
sendto()
```

menghasilkan satu datagram UDP.

Receiver mengambil satu datagram melalui:

```python
recvfrom()
```

selama ukuran buffer cukup.

Pada aplikasi ini heartbeat dikirim dalam bentuk JSON:

```json
{
  "type": "ping",
  "seq": 1,
  "client_send_time": 123456789
}
```

Setiap ping mempunyai sequence number:

```text
seq = 1
seq = 2
seq = 3
...
seq = 10
```

Sequence number digunakan untuk memastikan response yang diterima sesuai dengan request yang sedang dihitung RTT-nya.

---

# 13. Hasil Pengujian UDP

Masukkan hasil terminal UDP client pada bagian berikut.

Contoh format:

```text
Ping 1 : RTT = ........ ms
Ping 2 : RTT = ........ ms
Ping 3 : RTT = ........ ms
Ping 4 : RTT = ........ ms
Ping 5 : RTT = ........ ms
Ping 6 : RTT = ........ ms
Ping 7 : RTT = ........ ms
Ping 8 : RTT = ........ ms
Ping 9 : RTT = ........ ms
Ping 10: RTT = ........ ms
```

Hasil statistik:

| Parameter | Hasil |
|---|---:|
| Paket dikirim | 10 |
| Paket diterima | ........ |
| Paket hilang | ........ |
| Packet loss | ........ % |
| RTT minimum | ........ ms |
| RTT rata-rata | ........ ms |
| RTT maksimum | ........ ms |

Karena pengujian dilakukan pada localhost, nilai RTT biasanya sangat kecil dan packet loss umumnya 0%. Akan tetapi, hasil sebenarnya harus mengikuti output program saat pengujian dilakukan.

---

# 14. Pengujian Explicit Bind pada UDP Client

Secara default, client UDP tidak menentukan local port secara manual.

Saat:

```python
client_socket.sendto(...)
```

dijalankan, sistem operasi memilih sebuah ephemeral port.

Untuk eksperimen explicit bind digunakan:

```python
client_socket.bind(("", 5432))
```

Program dijalankan dengan:

```powershell
python UDPClient.py --bind-port 5432
```

---

## 14.1 Hasil Wireshark

Pada request dapat terlihat:

```text
Source Port      : 5432
Destination Port : 12001
```

Pada response:

```text
Source Port      : 12001
Destination Port : 5432
```

### Bukti Wireshark

> **Sisipkan screenshot explicit bind UDP di sini.**

```md
![UDP Explicit Bind](images/udp_bind_5432.png)
```

### Analisis

Server tetap dapat membalas client karena server mengetahui source IP dan source port melalui `recvfrom()`.

Dengan explicit bind, client memaksa socket UDP menggunakan port lokal 5432.

Jika terdapat dua aplikasi client pada host yang sama dan keduanya melakukan:

```python
bind(("", 5432))
```

maka client kedua pada konfigurasi normal dapat mengalami error:

```text
Address already in use
```

Hal tersebut terjadi karena port lokal 5432 telah digunakan oleh socket pertama.

---

# 15. Byte Stream TCP vs Message Boundary UDP

Perbedaan utama dapat dirangkum sebagai berikut:

| Karakteristik | TCP | UDP |
|---|---|---|
| Jenis socket | `SOCK_STREAM` | `SOCK_DGRAM` |
| Connection | Connection-oriented | Connectionless |
| Reliability | Ya | Tidak dijamin |
| Ordering | Ya | Tidak dijamin |
| Message boundary | Tidak | Ya |
| Connection socket per client | Ya | Tidak |
| Cocok untuk file | Ya | Umumnya tidak tanpa reliability tambahan |
| Cocok untuk heartbeat sederhana | Bisa, tetapi lebih berat | Ya |

Pada TCP, aplikasi harus membangun mekanisme framing sendiri.

Pada UDP, setiap datagram sudah mempunyai batas pesan secara alami.

---

# 16. Analisis Skalabilitas Socket

Untuk `N` client TCP aktif, server memiliki:

```text
1 welcoming socket
+
N connection socket
=
N + 1 socket
```

Hal ini terjadi karena setiap koneksi TCP mempertahankan state tersendiri.

Sebaliknya, UDP server hanya membutuhkan:

```text
1 socket
```

untuk menerima paket dari banyak client.

Implikasinya, UDP membutuhkan lebih sedikit file descriptor pada sisi server.

Namun UDP tidak memberikan fitur reliability dan ordering seperti TCP. Apabila fitur tersebut diperlukan, aplikasi harus mengimplementasikannya sendiri.

---

# 17. QUIC dan Head-of-Line Blocking

QUIC digunakan oleh HTTP/3 dan berjalan di atas UDP.

Salah satu alasan penggunaan UDP adalah agar QUIC dapat mengimplementasikan mekanisme transport modern pada user space tanpa harus membuat protokol transport baru yang kemungkinan diblokir atau tidak dikenali oleh perangkat jaringan seperti firewall, NAT, dan middlebox.

Jika QUIC berjalan di atas TCP, QUIC akan mewarisi karakteristik TCP berupa byte stream serta transport-level Head-of-Line (HOL) blocking.

Dalam TCP, jika sebuah segmen hilang, data setelah segmen tersebut tidak dapat diberikan ke aplikasi sampai segmen yang hilang berhasil diterima kembali.

QUIC mengimplementasikan beberapa stream independen di dalam satu connection.

Secara konseptual:

```text
QUIC Connection
|
+-- Stream A
+-- Stream B
+-- Stream C
```

Apabila paket pada Stream A hilang, Stream B dan Stream C yang datanya sudah lengkap tetap dapat diproses.

Dengan demikian QUIC mengurangi transport-level HOL blocking antarstream.

Ordering tetap berlaku di dalam stream yang sama.

---

# 18. Kesimpulan

Berdasarkan implementasi dan pengujian yang dilakukan, dapat disimpulkan bahwa TCP dan UDP mempunyai karakteristik transport yang berbeda dan sesuai untuk kebutuhan yang berbeda.

TCP digunakan pada sistem untuk pengiriman pesan dan file karena memberikan reliable dan ordered delivery. Server TCP menggunakan satu welcoming socket dan satu connection socket untuk setiap client. Agar dapat menangani beberapa client secara bersamaan, server menggunakan multithreading.

TCP tidak memiliki message boundary karena menyediakan abstraksi byte stream. Oleh karena itu sistem mengimplementasikan application-layer framing menggunakan 4-byte length header.

UDP digunakan untuk heartbeat dan pengukuran RTT karena mempunyai overhead lebih rendah dan tidak membutuhkan proses connection establishment. Client mengirimkan 10 ping dengan timeout 1 detik dan menghitung RTT serta packet loss.

Capture Wireshark memperlihatkan perbedaan yang jelas. TCP melakukan three-way handshake sebelum pertukaran data, sedangkan UDP langsung mengirimkan datagram tanpa proses handshake.

Pengujian explicit bind juga menunjukkan bahwa UDP client dapat menggunakan port lokal tertentu, misalnya 5432, dan server tetap dapat memberikan response ke port tersebut.

Secara keseluruhan, implementasi hybrid socket menunjukkan bahwa pemilihan protokol transport sebaiknya disesuaikan dengan kebutuhan aplikasi. TCP lebih sesuai ketika reliability dan ordering menjadi prioritas, sedangkan UDP sesuai untuk komunikasi sederhana yang membutuhkan overhead rendah dan tidak memerlukan koneksi persisten.

---

# 19. Daftar Bukti yang Perlu Disertakan

Sebelum laporan dikumpulkan, pastikan screenshot berikut sudah dimasukkan:

1. TCP Three-Way Handshake (`SYN`, `SYN-ACK`, `ACK`).
2. TCP Data Transfer pada port `12000`.
3. UDP heartbeat request-response pada port `12001`.
4. UDP explicit bind port `5432` (opsional tetapi disarankan).
5. Output terminal UDP yang menunjukkan RTT dan packet loss.

Filter Wireshark yang digunakan:

```text
tcp.port == 12000
```

dan:

```text
udp.port == 12001
```

---

# 20. Referensi

Kurose, J. F., & Ross, K. W. *Computer Networking: A Top-Down Approach*, 9th Edition, Section 2.6 dan Chapter 2 Review Problems.
