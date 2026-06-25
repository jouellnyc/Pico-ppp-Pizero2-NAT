"""

Expected Output

============================================================
[00] STARTING REQUEST
============================================================
  [+] DNS Resolved: 142.251.45.78 (took 29ms)
  [+] TCP Handshake Complete (took 27ms)
  [->] Sent Payload (36 bytes)
  [<-] First Inbound Byte Detected (Latency/TTFB: 150ms)
      |-- Chunk 00: Received 512 bytes (Total Buffer: 512/2048)
      |-- Chunk 01: Received 261 bytes (Total Buffer: 773/2048)
  [+] Clean EOF (FIN packet received from server)
------------------------------------------------------------
[00] SUCCESS SUMMARY:
  * Total Bytes Gathered: 773 bytes
  * HTTP Status Line:     b'HTTP/1.0 301 Moved Permanently'
  * Internal Timings:
    - DNS Resolution:     29 ms
    - TCP Connection:     27 ms
    - Time to First Byte: 150 ms
    - Grand Total Time:   214 ms
------------------------------------------------------------
"""

import socket
import gc
import time
import select
import machine
import network

def run_request(index):
    gc.collect()
    s = None
    
    # Timing tracking variables
    t_start = time.ticks_ms()
    t_dns = 0
    t_connected = 0
    t_first_byte = 0
    t_done = 0
    
    print("\n" + "="*60)
    print("[{:02d}] STARTING REQUEST".format(index))
    print("="*60)
    
    try:
        # 1. DNS Resolution
        dns_start = time.ticks_ms()
        ai = socket.getaddrinfo("google.com", 80)
        addr = ai[0][-1]
        t_dns = time.ticks_diff(time.ticks_ms(), dns_start)
        print("  [+] DNS Resolved: {} (took {}ms)".format(addr[0], t_dns))
        
        # 2. Socket Creation & Connect
        s = socket.socket()
        s.setblocking(False)
        
        connect_start = time.ticks_ms()
        try:
            s.connect(addr)
        except OSError as e:
            if e.args[0] != 115: # EINPROGRESS
                raise e
                
        _, w, _ = select.select([], [s], [], 3.0)
        if not w:
            raise OSError("Connect Timeout")
        t_connected = time.ticks_diff(time.ticks_ms(), connect_start)
        print("  [+] TCP Handshake Complete (took {}ms)".format(t_connected))
            
        # 3. Transmission
        payload = b"GET / HTTP/1.0\r\nHost: google.com\r\n\r\n"
        s.send(payload)
        print("  [->] Sent Payload ({} bytes)".format(len(payload)))
        
        response = b""
        
        # --- PHASE 1: WAIT FOR FIRST INBOUND BYTE ---
        first_byte_start = time.ticks_ms()
        first_byte_arrived = False
        
        for _ in range(40): 
            r, _, _ = select.select([s], [], [], 0.1)
            if r:
                first_byte_arrived = True
                break
            time.sleep_ms(50)
            
        if not first_byte_arrived:
            print("  [!] FAIL - Remote host did not respond in time")
            return
            
        t_first_byte = time.ticks_diff(time.ticks_ms(), first_byte_start)
        print("  [<-] First Inbound Byte Detected (Latency/TTFB: {}ms)".format(t_first_byte))

        # --- PHASE 2: STREAM DATA IN CHUNKS ---
        stream_start = time.ticks_ms()
        stall_count = 0
        chunk_index = 0
        
        while True:
            r, _, _ = select.select([s], [], [], 0.2)
            if r:
                try:
                    data = s.recv(512)
                    if data:
                        chunk_len = len(data)
                        response += data
                        print("      |-- Chunk {:02d}: Received {} bytes (Total Buffer: {}/2048)".format(
                            chunk_index, chunk_len, len(response)
                        ))
                        chunk_index += 1
                        stall_count = 0 
                    else:
                        print("  [+] Clean EOF (FIN packet received from server)")
                        break 
                except OSError as e:
                    if e.args[0] == 11: # EAGAIN
                        time.sleep_ms(30)
                        continue
                    else:
                        raise e
            else:
                stall_count += 1
                if stall_count > 5:
                    print("  [!] Stream Idle - Timeout window closed after 1000ms gap")
                    break
                    
            if time.ticks_diff(time.ticks_ms(), stream_start) > 6000: 
                print("  [!] Hard execution safety timeout triggered (6000ms)")
                break
                
        t_done = time.ticks_diff(time.ticks_ms(), t_start)
        
        # --- METRICS SUMMARY ---
        first_line = response.split(b"\r\n")[0] if response else b"NO DATA"
        print("-" * 60)
        print("[{:02d}] SUCCESS SUMMARY:".format(index))
        print("  * Total Bytes Gathered: {} bytes".format(len(response)))
        print("  * HTTP Status Line:     {}".format(first_line))
        print("  * Internal Timings:")
        print("    - DNS Resolution:     {} ms".format(t_dns))
        print("    - TCP Connection:     {} ms".format(t_connected))
        print("    - Time to First Byte: {} ms".format(t_first_byte))
        print("    - Grand Total Time:   {} ms".format(t_done))
        print("-" * 60)
        
    except Exception as e:
        print("  [X] FAIL - Exception on line {}: {}".format(index, e))
        
    finally:
        if s is not None:
            try:
                s.close()
            except:
                pass

# --- Execution Loop ---
print("Running persistent serialization-aware loop with telemetry...")
for i in range(10):
    run_request(i)
    gc.collect()
    time.sleep_ms(200)
    time.sleep_ms(1300) # Cooldown pacing
    


