# 🛡️ EdgeGuard — System Architecture & Threat Taxonomy

This document outlines the system topology, 13 canonical streaming features, and embedded ONNX inference runtime powering **EdgeGuard**.

---

## 1. Architectural Highlights
- **Automotive CAN Ingestion**: SocketCAN native Linux interface / MCP2515 SPI controller supporting high-speed frame rates up to 2,000 frames/sec.
- **Embedded ONNX Engine**: ONNX Runtime 1.17.1 evaluation embedded inside Java 17 / Spring Boot 3.3.5 with sub-1.2ms per-frame classification latency.
- **13 Canonical Streaming Features**: Real-time sliding-window extraction of temporal intervals, ID Shannon entropy, payload bitwise entropy, and priority saturation ratios.
- **National SOC Console**: Electron 45 and React 19 real-time dashboard displaying ECU network topology, forensic frame traces, and acoustic severity alarms.

---

## 2. Technical Documentation & Formal Report
The complete 12-page IEEE-standard technical architecture report is published in:
- **LaTeX Source**: [`docs/report/project-report.tex`](file:///c:/Users/tharu/Documents/GITHUB%20REPO/GITHUB%20MANAGER/EdgeGuard/docs/report/project-report.tex)
- **Compiled PDF**: [`docs/report/project-report.pdf`](file:///c:/Users/tharu/Documents/GITHUB%20REPO/GITHUB%20MANAGER/EdgeGuard/docs/report/project-report.pdf)
