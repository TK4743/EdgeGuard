# EdgeGuard Test Architecture & Infrastructure (`TEST_INFRA.md`)

## 1. Executive Summary & Test Philosophy

EdgeGuard is an automotive intrusion detection system (IDS) protecting vehicle Controller Area Network (CAN) bus communications. In an automotive cyber-physical deployment, detection latency, classification accuracy, bit-level mathematical parity, and zero downtime under stream saturation are safety-critical requirements.

This document formalizes the **4-Tier Test Architecture** for EdgeGuard across all four subsystems:
- **`ml-sidecar/`**: Feature extraction pipeline and edge-quantized ONNX classifier.
- **`backend/`**: Java 17 Spring Boot high-throughput ingestion engine, ONNX Runtime native bridge, and STOMP message broker.
- **`frontend/`**: Real-time React 18 + Vite telemetry dashboard and incident register.
- **`desktop/`**: Hardened Electron Chromium sandbox wrapper.

---

## 2. Multi-Tier Test Architecture

```
+-----------------------------------------------------------------------------+
|                                TIER 4                                       |
|               REAL-WORLD TELEMETRY & SUSTAINED STREAM REPLAY                |
|  - 100+ Frame Temporal Stream Replay    - Sub-millisecond Inference Latency |
|  - Memory Stability & Leak Detection    - Continuous Alert Broadcast        |
+-----------------------------------------------------------------------------+
                                      ▲
                                      │
+-----------------------------------------------------------------------------+
|                                TIER 3                                       |
|                   CROSS-SUBSYSTEM & STOMP INTEGRATION                       |
|  - Raw WebSocket /ws/alerts Handshake   - STOMP Protocol Negotiation        |
|  - Topic /topic/alerts Subscription    - End-to-End Ingest -> STOMP Payload |
+-----------------------------------------------------------------------------+
                                      ▲
                                      │
+-----------------------------------------------------------------------------+
|                                TIER 2                                       |
|                      BOUNDARY & CORNER CASES (BVA)                          |
|  - 0x/0X Hex Prefix Stripping          - DLC Boundaries (0, 1, 7, 8, 99)   |
|  - Payload Hex Limits (00..FF, Invalid) - HTTP 400 Bad Request Rejections   |
+-----------------------------------------------------------------------------+
                                      ▲
                                      │
+-----------------------------------------------------------------------------+
|                                TIER 1                                       |
|                     FEATURE COVERAGE & SPECIFICATION                        |
|  - Valid Normal CAN Frames (Class 0)   - DoS Flood Ingestion (Class 1)      |
|  - Fuzzy Attack Ingestion (Class 2)    - Spoofing Attack Ingestion (Class 3)|
|  - 13-Feature Bit-Parity (< 1e-4)      - Zero-Secret Security Compliance    |
+-----------------------------------------------------------------------------+
```

---

## 3. Test Engineering Methodology

### 3.1 Category-Partitioning Method
We divide the CAN frame domain into disjoint equivalence classes:
1. **CAN ID Partition**:
   - Standard Known Top-5 IDs (`043f`, `0002`, `02c0`, `018f`, `0316`) -> Evaluated against one-hot encoded top-5 slots.
   - DoS Dominant ID (`0000`) -> Highest bus priority, triggers DoS state machine.
   - Arbitrary/Random Hex IDs (`05F8`, `0218`, `07FF`) -> Characteristic of Fuzzy injection attacks.
   - 0x-prefixed representations (`0x043f`, `0X0000`).
2. **Payload Partition**:
   - Uniform Byte Patterns (`00 00 00 00 00 00 00 00` -> zero entropy, zero variance).
   - High-Entropy Injections (`random [0..255]` -> max entropy ~3.0, high byte variance).
   - Real-World Telemetry Bytes (`10 40 60 ff 79 7b 0c 00`).
3. **Data Length Code (DLC) Partition**:
   - Standard full payload (`DLC = 8`).
   - Boundary payload sizes (`DLC = 0, 1, 7`).
   - Invalid payload sizes (`DLC < 0` or `DLC > 8`).
4. **Transmission Flag Partition**:
   - Regular Reception (`R`).
   - Injected / Transmitted (`T`).

### 3.2 Boundary Value Analysis (BVA)
EdgeGuard tests boundaries where off-by-one errors or overflow conditions commonly occur:
- **DLC Boundaries**: Test values `-1` (invalid), `0` (valid minimum), `1` (valid small), `7` (valid near-full), `8` (valid maximum), `9` and `99` (invalid).
- **Hex Byte Encodings**: Test byte minimum `0x00`, boundary transitions `0x7F` / `0x80`, maximum `0xFF`, and non-hex corruption (`NOT_HEX`, `ZZ`).
- **CAN ID Encodings**: Minimum 11-bit ID (`0000`), maximum standard 11-bit ID (`07FF`), 29-bit extended IDs (`1FFFFFFF`), empty strings (`""`), whitespace, and non-hex text.
- **Temporal Windows**: Sliding window warmup at boundaries `N = 1`, `N = 50` (full window), and `N = 51` (eviction of oldest ID).

### 3.3 Combinatorial / Pairwise Testing
Combinations of CAN ID formatting (raw hex vs `0x`-prefixed), payload length (0 to 8 bytes), and message transmission flags are exercised together to ensure parser robustness across all inputs.

### 3.4 Real-World Stream Replay
Simulates genuine automotive driving conditions:
- 100+ sequential CAN bus frames evaluated in real-time order.
- Stateful feature tracking: Time Delta ($\Delta t$), Payload Entropy ($H$), Byte Variance ($\sigma^2$), Hamming Weight, 50-packet sliding window frequency, and inter-arrival variance.
- Measurement of inference latency ensuring strict sub-millisecond execution ($< 1.0\text{ ms}$).

---

## 4. Test Suite Inventory

| Tier | Component | File Path | Focus Area | Framework |
| :--- | :--- | :--- | :--- | :--- |
| **Tier 1** | Security | `tests/secret_scan.py` | Zero secret exposure scan (.env, keys, tokens) | Python 3 |
| **Tier 1** | ML Pipeline | `ml-sidecar/test_features.py` | 13-feature vector extraction correctness | Python / NumPy |
| **Tier 1** | Parity | `ml-sidecar/test_parity.py` | 100-vector numerical parity (< 1e-4 diff) | Python / Pandas |
| **Tier 1** | Backend Parity | `backend/src/test/.../ParityTest.java` | Java ONNX vs Python 13-feature parity | JUnit 5 / ONNX |
| **Tier 1** | Frontend | `frontend/src/__tests__/*.test.tsx` | UI components, KPI metrics, threat breakdown | Vitest / RTL |
| **Tier 2** | Backend REST | `backend/src/test/.../CanDataControllerTest.java` | REST input validation & 400 error codes | Spring MockMvc |
| **Tier 2** | Boundary E2E | `tests/e2e_integration_test.py` (Tier 2) | 0x prefix, DLC limits, malformed payload | Python Requests |
| **Tier 3** | STOMP E2E | `tests/e2e_integration_test.py` (Tier 3) | WebSocket handshake & STOMP /topic/alerts | WebSocket / STOMP |
| **Tier 4** | Telemetry E2E | `tests/e2e_integration_test.py` (Tier 4) | 100+ frame stream replay & latency SLA | Python / Multi-thread |

---

## 5. Execution & Verification Commands

### 5.1 Repository-Wide Security Scan (Tier 1)
```powershell
python tests/secret_scan.py
```
*Criteria*: Exit code 0, 0 violations detected.

### 5.2 Backend Unit & Integration Tests (Tiers 1 & 2)
```powershell
cd backend
.\mvnw.cmd test
```
*Criteria*: 12 tests passed, 0 failures, 0 errors.

### 5.3 Frontend Unit & Regression Tests (Tier 1)
```powershell
cd frontend
npm test
```
*Criteria*: 7 test files passed, 16 tests passed.

### 5.4 Cross-Subsystem E2E Integration Suite (Tiers 1, 2, 3, 4)
```powershell
python tests/e2e_integration_test.py
```
*Criteria*: 100% test cases pass across all 4 tiers, exit code 0.
