---

## Deep Dive: The MTU vs. UART Buffer Relationship

A common point of failure when bridging microcontrollers to Linux network daemons is misconfiguring the Maximum Transmission Unit (MTU) relative to the physical hardware serial buffers.

### The Network Layer: MTU/MRU must be 1500

MicroPython handles its network routing via **lwIP**, a lightweight TCP/IP stack compiled natively to expect a standard Ethernet MTU of **1500 bytes**.

If the Pi's `pppd` daemon forces an intentional bottleneck down to `512` bytes via `mru 512`, it sends an initial Link Control Protocol (LCP) configuration request demanding that the client restrict its maximum payload bounds. MicroPython rejects this structural mismatch and ignores the frame entirely. Forcing **1500** on both sides ensures the link layer completes its handshake instantly.

### The Hardware Layer: `rxbuf` must be 2048

While the network layer operates on 1500-byte boundaries, the underlying raw serial stream is wrapped in dynamic PPP asynchronous framing bytes (flags, control checks, and headers), inflating the total footprint of a full network burst.

MicroPython defaults to a highly restrictive 256-byte hardware UART ring buffer. Because the Pi Zero bursts data down the line at 115,200 bps, a single incoming 1500-byte payload will instantly overflow a default UART bucket if the Pico is occupied with garbage collection or thread execution. Scaling the hardware allocation to **2048 bytes** ensures the Pico has a large enough memory cushion to safely hold complete, back-to-back network frames until the runtime can process them.

| Layer | Parameter | Target Value | Purpose |
| --- | --- | --- | --- |
| **Network (Software)** | `mtu` / `mru` | **1500** | Prevents lwIP parameter rejection; matches standard web architectures. |
| **Hardware (Physical)** | `rxbuf` | **2048** | Prevents hardware buffer overflows during continuous downstream bursts. |

---
