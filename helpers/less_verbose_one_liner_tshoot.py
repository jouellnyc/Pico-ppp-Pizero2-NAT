
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


