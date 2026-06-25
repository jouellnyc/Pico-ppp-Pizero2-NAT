"""
Expected output:

Running single-line telemetry loop...
[00] OK - Read 773 bytes | DNS: 26ms | TCP: 32ms | TTFB: 118ms | Total: 177ms | b'HTTP/1.0 301 Moved Permanently'
[01] OK - Read 773 bytes | DNS: 0ms | TCP: 35ms | TTFB: 114ms | Total: 150ms | b'HTTP/1.0 301 Moved Permanently'
[02] OK - Read 773 bytes | DNS: 0ms | TCP: 30ms | TTFB: 118ms | Total: 149ms | b'HTTP/1.0 301 Moved Permanently'
[03] OK - Read 773 bytes | DNS: 0ms | TCP: 32ms | TTFB: 112ms | Total: 145ms | b'HTTP/1.0 301 Moved Permanently'
[04] OK - Read 773 bytes | DNS: 0ms | TCP: 30ms | TTFB: 121ms | Total: 152ms | b'HTTP/1.0 301 Moved Permanently'
[05] OK - Read 773 bytes | DNS: 0ms | TCP: 32ms | TTFB: 113ms | Total: 146ms | b'HTTP/1.0 301 Moved Permanently'
[06] OK - Read 773 bytes | DNS: 0ms | TCP: 29ms | TTFB: 110ms | Total: 140ms | b'HTTP/1.0 301 Moved Permanently'
[07] OK - Read 773 bytes | DNS: 0ms | TCP: 29ms | TTFB: 119ms | Total: 149ms | b'HTTP/1.0 301 Moved Permanently'
[08] OK - Read 773 bytes | DNS: 0ms | TCP: 33ms | TTFB: 119ms | Total: 153ms | b'HTTP/1.0 301 Moved Permanently'
[09] OK - Read 773 bytes | DNS: 0ms | TCP: 31ms | TTFB: 111ms | Total: 143ms | b'HTTP/1.0 301 Moved Permanently'

""""

import socket, gc, time, select, machine, network

def run_request(idx):
    gc.collect(); s = None; t0 = time.ticks_ms()
    try:
        # 1. DNS Resolution
        t_dns0 = time.ticks_ms()
        addr = socket.getaddrinfo("google.com", 80)[0][-1]
        tdns = time.ticks_diff(time.ticks_ms(), t_dns0)
        
        # 2. Non-blocking TCP Connect
        s = socket.socket(); s.setblocking(False)
        t_con0 = time.ticks_ms()
        try:
            s.connect(addr)
        except OSError as e:
            if e.args[0] != 115:
                raise e
                
        if not select.select([], [s], [], 3.0)[1]: 
            raise OSError("Timeout")
        tcon = time.ticks_diff(time.ticks_ms(), t_con0)
        
        # 3. Transmission & TTFB Wait
        s.send(b"GET / HTTP/1.0\r\nHost: google.com\r\n\r\n")
        t_fb0 = time.ticks_ms()
        if not select.select([s], [], [], 4.0)[0]: 
            raise OSError("Timeout")
        ttfb = time.ticks_diff(time.ticks_ms(), t_fb0)
        
        # 4. Stream Inbound Payload
        res = b""
        while select.select([s], [], [], 0.2)[0]:
            try:
                d = s.recv(512); res += d
                if not d: 
                    break
            except OSError as e:
                if e.args[0] == 11:
                    time.sleep_ms(30)
                    continue
                raise e
        
        # 5. Single-Line Metrics Output
        ttot = time.ticks_diff(time.ticks_ms(), t0)
        status = res.split(b'\r\n')[0] if res else b"NO DATA"
        print(f"[{idx:02d}] OK - Read {len(res)} bytes | DNS: {tdns}ms | TCP: {tcon}ms | TTFB: {ttfb}ms | Total: {ttot}ms | {status}")
        
    except Exception as e: 
        print(f"[{idx:02d}] FAIL: {e}")
    finally: 
        if s: 
            s.close()

# --- Execution Loop ---
print("Running single-line telemetry loop...")
for i in range(10): 
    run_request(i)
    gc.collect()
    time.sleep_ms(1500)


