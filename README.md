# Raspberry Pi Pico — Internet via PPP over UART (Pi Zero NAT)

## What This Is

A Raspberry Pi Pico H or W connected to the internet via a Raspberry Pi
Zero 2W acting as a PPP/NAT gateway over a UART serial link. The Pi Zero
handles WPA2 Enterprise WiFi (or any network connection) and shares it
with the Pico over three wires.

## Some Whys

- Pico W cannot do WPA2 Enterprise natively
- Pico H was never intended to connect to the network
- PPP support landed in MicroPython rp2 master June 2026
- Three jumper wires is all the hardware needed

## Hardware

- Raspberry Pi Pico H or W
- Raspberry Pi Zero 2W (Zero 1 should work too)
- 3 jumper wires (TX, RX, GND)

**Wiring:**
```
Pico GP4 (TX) → Pi Zero GPIO15 (RX) — physical pin 10
Pico GP5 (RX) → Pi Zero GPIO14 (TX) — physical pin 8
Pico GND      → Pi Zero GND          — physical pin 6
```

---

## Pi Zero Setup

### 1. Disable Bluetooth to free the real UART

Without this, Bluetooth owns `/dev/ttyAMA0` and pppd sees its own frames
looped back.

```bash
echo 'dtoverlay=disable-bt' | sudo tee -a /boot/firmware/config.txt
reboot
```

### 2. Kernel config (/etc/sysctl.conf)

```
net.ipv4.ip_forward=1
net.ipv4.conf.all.rp_filter=0
net.ipv4.conf.default.rp_filter=0
net.ipv4.conf.wlan0.rp_filter=0
```

Note: `ppp0` rp_filter is handled dynamically at link-up time (see step 5).

Apply immediately:
```bash
sysctl -p
```

### 3. DNS (/etc/ppp/options)

Pushes DNS servers to the Pico via IPCP during PPP negotiation.
The Pico will automatically use them for `socket.getaddrinfo()`.

```
ms-dns 8.8.8.8
ms-dns 8.8.4.4
```

### 4. NAT/Firewall

```bash
iptables -t nat -A POSTROUTING -o wlan0 -j MASQUERADE
iptables -A FORWARD -i ppp0 -o wlan0 -j ACCEPT
iptables -A FORWARD -i wlan0 -o ppp0 -m state --state RELATED,ESTABLISHED -j ACCEPT
iptables-save > /etc/iptables/rules.v4
```

### 5. TX Queue and rp_filter — Dynamic Link Hook (Recommended)

Rather than configuring `ppp0` in `sysctl.conf` before the interface
exists, apply both settings the moment the link comes up. This avoids
startup errors and guarantees the configuration binds correctly every time.

```bash
sudo tee /etc/ppp/ip-up.d/99-txqueuelen << 'EOF'
#!/bin/sh
# $1 contains the active interface name (e.g., ppp0)
ip link set $1 txqueuelen 100
sysctl -w net.ipv4.conf.$1.rp_filter=0
EOF
sudo chmod +x /etc/ppp/ip-up.d/99-txqueuelen
```

### 6. PPP startup script (/etc/ppp/ppp-start.sh)

```bash
#!/bin/sh -e
sysctl -p
stty -F /dev/ttyAMA0 raw -echo -echoe -echok
exec pppd /dev/ttyAMA0 115200 10.0.5.1:10.0.5.2 \
    proxyarp local noauth debug nodetach dump \
    nocrtscts passive persist maxfail 0 holdoff 1 \
    mtu 1500 mru 1500
```

```bash
chmod +x /etc/ppp/ppp-start.sh
```

### 7. Auto-start on boot (/etc/rc.local)

```bash
#!/bin/sh -e
/etc/ppp/ppp-start.sh &
exit 0
```

---

## Pico H or W — MicroPython

PPP support is enabled by default for Pico W in MicroPython master as of
June 2026. Build from source or use a recent nightly. For Pico H, build
your own firmware (see official MicroPython docs).

### Critical: rxbuf=2048 is required

The default UART receive buffer is too small for PPP HTTP responses and
causes intermittent `recv()` timeouts (~90% failure rate without this).

### Connect

```python
import machine, network, socket, time

uart = machine.UART(1, baudrate=115200, tx=4, rx=5, rxbuf=2048)
ppp = network.PPP(uart)
ppp.connect()

while not ppp.isconnected():
    time.sleep_ms(100)
    pass

print(ppp.ifconfig())
# ('10.0.5.2', '255.255.255.255', '10.0.5.1', '8.8.8.8')
```

### HTTP Example

```python
def http_get(host, path="/"):
    addr = socket.getaddrinfo(host, 80)[0][-1]
    s = socket.socket()
    s.settimeout(5.0)
    s.connect(addr)
    s.send(f"GET {path} HTTP/1.0\r\nHost: {host}\r\n\r\n".encode())
    data = s.recv(1024)
    s.close()
    return data

print(http_get("google.com"))
```

---

## Lessons Learned

- `dtoverlay=disable-bt` is required on Pi Zero 2W — without it Bluetooth
  owns `/dev/ttyAMA0` and pppd sees its own output looped back
- `rxbuf=2048` on the UART is not optional — without it `recv()` fails
  ~90% of the time due to buffer overflow on inbound HTTP responses
- `ip_forward` does not survive reboot without `sysctl -p` in the startup
  script
- NAT MASQUERADE rule must specify `-o wlan0` explicitly
- `ms-dns` in `/etc/ppp/options` pushes DNS to the Pico automatically via
  IPCP — no manual DNS config needed on the Pico
- Setting `ppp0` rp_filter in `sysctl.conf` throws errors at boot because
  the interface does not exist yet — apply it dynamically in
  `/etc/ppp/ip-up.d/` instead

---

## Tested On

- Raspberry Pi Pico W (RP2040) — MicroPython v1.29.0-preview.417
- Raspberry Pi Pico H (RP2040) — MicroPython custom build
- Raspberry Pi Zero 2W — Raspberry Pi OS Bookworm
- 10/10 consecutive HTTP requests successful
