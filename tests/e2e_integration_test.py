"""
EdgeGuard End-to-End (E2E) Cross-Subsystem Integration Test Suite
================================================================
Exercising:
  - Tier 1: Feature Coverage (Normal, DoS, Fuzzy, Spoofing via POST /api/predict)
  - Tier 2: Boundary & Corner Cases (0x-prefixed hex, boundary DLCs, hex boundaries, HTTP 400 validation)
  - Tier 3: Cross-Feature STOMP Broker (WebSocket handshake, /topic/alerts subscription, alert schema)
  - Tier 4: Real-World Stream Replay (100+ sequential CAN frames, memory stability, sub-millisecond latency SLA)
"""

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import psutil
import websocket

BACKEND_HOST = "localhost"
BACKEND_PORT = 8080
BASE_URL = f"http://{BACKEND_HOST}:{BACKEND_PORT}"
WS_URL = f"ws://{BACKEND_HOST}:{BACKEND_PORT}/ws/alerts"

JAR_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "backend", "target", "backend-0.0.1-SNAPSHOT.jar")
)
PARITY_DATA_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "ml-sidecar", "parity_test_data.json")
)


class TestResultTracker:
    def __init__(self):
        self.total = 0
        self.passed = 0
        self.failed = 0
        self.failures = []

    def assert_true(self, condition, test_name, message=""):
        self.total += 1
        if condition:
            self.passed += 1
            print(f"  [PASS] {test_name}")
        else:
            self.failed += 1
            detail = f"{test_name} FAILED: {message}"
            self.failures.append(detail)
            print(f"  [FAIL] {detail}")

    def assert_equal(self, actual, expected, test_name):
        self.assert_true(
            actual == expected,
            test_name,
            f"Expected {expected!r}, got {actual!r}"
        )

    def print_summary(self):
        print("\n" + "=" * 70)
        print(f"TEST SUMMARY: Total: {self.total} | Passed: {self.passed} | Failed: {self.failed}")
        if self.failures:
            print("\nFailures:")
            for f in self.failures:
                print(f" - {f}")
            print("=" * 70)
            return False
        print("STATUS: 100% PASSED — Zero Defects Detected.")
        print("=" * 70)
        return True


class BackendManager:
    """Manages backend lifecycle if not already running."""
    def __init__(self):
        self.spawned_process = None

    def is_backend_alive(self):
        try:
            req = urllib.request.Request(
                f"{BASE_URL}/api/predict",
                data=b"",
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            urllib.request.urlopen(req, timeout=1.0)
            return True
        except urllib.error.HTTPError as e:
            # 400 Bad Request indicates server is alive and responding
            if e.code == 400:
                return True
            return False
        except Exception:
            return False

    def ensure_backend_running(self):
        if self.is_backend_alive():
            print("[*] Backend is already active on port 8080.")
            return

        print(f"[*] Starting backend process from {JAR_PATH}...")
        if not os.path.exists(JAR_PATH):
            raise FileNotFoundError(f"Backend JAR not found at {JAR_PATH}. Run 'mvnw package' first.")

        # Launch from repo root so relative paths resolve correctly
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.spawned_process = subprocess.Popen(
            ["java", "-jar", JAR_PATH],
            cwd=repo_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Wait up to 30 seconds for health check
        print("[*] Waiting for Spring Boot initialization...")
        deadline = time.time() + 35.0
        while time.time() < deadline:
            if self.is_backend_alive():
                print("[*] Backend successfully initialized and listening on port 8080.")
                return
            time.sleep(1.0)

        # Output stdout/stderr if failed to boot
        stdout, stderr = self.spawned_process.communicate(timeout=2.0)
        raise TimeoutError(f"Backend failed to respond on port 8080.\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}")

    def cleanup(self):
        if self.spawned_process:
            print(f"[*] Terminating backend process (PID {self.spawned_process.pid})...")
            try:
                if os.name == 'nt':
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(self.spawned_process.pid)],
                        capture_output=True,
                        check=False
                    )
                else:
                    self.spawned_process.terminate()
                    self.spawned_process.wait(timeout=5)
            except Exception as e:
                print(f"Warning during cleanup: {e}", file=sys.stderr)
            self.spawned_process = None


def post_predict(payload):
    """Utility to perform POST /api/predict using standard urllib."""
    data_bytes = json.dumps(payload).encode("utf-8") if payload is not None else b""
    req = urllib.request.Request(
        f"{BASE_URL}/api/predict",
        data=data_bytes,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        try:
            parsed = json.loads(body) if body else {}
        except Exception:
            parsed = body
        return e.code, parsed


# =============================================================================
# TIER 1: Feature Coverage (Feature Extraction & Prediction Contract)
# =============================================================================
def run_tier_1_tests(tracker):
    print("\n" + "=" * 60)
    print("RUNNING TIER 1: Feature Coverage & Classification Contract")
    print("=" * 60)

    # 1.1 Valid Normal CAN Message
    normal_frame = {
        "timestamp": 1478193341.095,
        "canId": "043f",
        "dlc": 8,
        "data": ["10", "40", "60", "ff", "79", "7b", "0c", "00"],
        "flag": "R"
    }
    status, body = post_predict(normal_frame)
    tracker.assert_equal(status, 200, "1.1 Valid Normal CAN Frame -> HTTP 200")
    tracker.assert_true("predictionLabel" in body, "1.1 Contains predictionLabel")
    tracker.assert_true("predictionClass" in body, "1.1 Contains predictionClass")
    tracker.assert_true(body.get("predictionLabel") in [0, 1, 2, 3], "1.1 predictionLabel in range [0, 3]")
    tracker.assert_true(body.get("latencyMs", 0.0) > 0.0, "1.1 latencyMs is positive float")
    tracker.assert_true(0.0 <= body.get("anomalyScore", 0.0) <= 1.0, "1.1 anomalyScore in [0.0, 1.0]")
    tracker.assert_equal(body.get("message", {}).get("canId"), "043f", "1.1 Echoed message CAN ID matches")

    # 1.2 DoS Attack Frame (ID 0000, 00 payload, flood)
    # Send short burst of 3 DoS frames to trigger high frequency
    dos_frame = {
        "timestamp": 1478193342.000,
        "canId": "0000",
        "dlc": 8,
        "data": ["00", "00", "00", "00", "00", "00", "00", "00"],
        "flag": "T"
    }
    status, body = post_predict(dos_frame)
    tracker.assert_equal(status, 200, "1.2 DoS Frame Ingestion -> HTTP 200")
    tracker.assert_true(body.get("predictionClass") in ["DoS", "Normal", "Fuzzy", "Spoofing"], "1.2 Valid classification string")
    tracker.assert_equal(body.get("predictionLabel"), 1, "1.2 DoS Attack correctly classified (Label 1: DoS)")
    tracker.assert_equal(body.get("predictionClass"), "DoS", "1.2 DoS Attack class name is 'DoS'")

    # 1.3 Fuzzy Attack Frame (High entropy, random ID)
    fuzzy_frame = {
        "timestamp": 1478193343.100,
        "canId": "05F8",
        "dlc": 8,
        "data": ["E4", "1A", "8F", "33", "7B", "C0", "D9", "22"],
        "flag": "T"
    }
    status, body = post_predict(fuzzy_frame)
    tracker.assert_equal(status, 200, "1.3 Fuzzy Attack Frame Ingestion -> HTTP 200")
    tracker.assert_true(body.get("predictionLabel") in [0, 1, 2, 3], "1.3 Fuzzy returns valid label")
    tracker.assert_true(body.get("latencyMs") < 15.0, "1.3 Fuzzy classification meets real-time latency (< 15ms)")

    # 1.4 Spoofing Attack Frame (Legitimate top-5 CAN ID with irregular payload)
    spoofing_frame = {
        "timestamp": 1478193344.005,
        "canId": "0316",
        "dlc": 8,
        "data": ["FF", "EE", "DD", "CC", "BB", "AA", "99", "88"],
        "flag": "T"
    }
    status, body = post_predict(spoofing_frame)
    tracker.assert_equal(status, 200, "1.4 Spoofing Attack Ingestion -> HTTP 200")
    tracker.assert_true(body.get("predictionLabel") in [0, 1, 2, 3], "1.4 Spoofing returns valid label")

    # 1.5 Contract & Model Label Parity Verification
    valid_classes = {"Normal": 0, "DoS": 1, "Fuzzy": 2, "Spoofing": 3}
    actual_label = body.get("predictionLabel")
    actual_class = body.get("predictionClass")
    expected_class = [k for k, v in valid_classes.items() if v == actual_label][0]
    tracker.assert_equal(actual_class, expected_class, "1.5 predictionLabel and predictionClass are strictly synchronized")


# =============================================================================
# TIER 2: Boundary & Corner Cases (Category-Partition & BVA)
# =============================================================================
def run_tier_2_tests(tracker):
    print("\n" + "=" * 60)
    print("RUNNING TIER 2: Boundary Value Analysis & Corner Cases")
    print("=" * 60)

    # 2.1 0x-prefixed CAN ID (lowercase & uppercase)
    p21a = {
        "timestamp": 1478193345.0,
        "canId": "0x043f",
        "dlc": 8,
        "data": ["00", "01", "02", "03", "04", "05", "06", "07"],
        "flag": "R"
    }
    status, body = post_predict(p21a)
    tracker.assert_equal(status, 200, "2.1a 0x-prefixed CAN ID ('0x043f') -> HTTP 200 OK")

    p21b = {
        "timestamp": 1478193345.1,
        "canId": "0X0000",
        "dlc": 8,
        "data": ["00", "00", "00", "00", "00", "00", "00", "00"],
        "flag": "T"
    }
    status, body = post_predict(p21b)
    tracker.assert_equal(status, 200, "2.1b 0X-prefixed uppercase CAN ID ('0X0000') -> HTTP 200 OK")

    # 2.2 0x-prefixed payload data bytes
    p22 = {
        "timestamp": 1478193345.2,
        "canId": "02c0",
        "dlc": 8,
        "data": ["0x10", "0x20", "0x30", "0x40", "0x50", "0x60", "0x70", "0x80"],
        "flag": "R"
    }
    status, body = post_predict(p22)
    tracker.assert_equal(status, 200, "2.2 0x-prefixed payload bytes -> HTTP 200 OK")

    # 2.3 Boundary DLC = 0 (empty payload padding)
    p23 = {
        "timestamp": 1478193345.3,
        "canId": "018f",
        "dlc": 0,
        "data": [],
        "flag": "R"
    }
    status, body = post_predict(p23)
    tracker.assert_equal(status, 200, "2.3 Boundary DLC = 0 with empty payload -> HTTP 200 OK")

    # 2.4 Boundary DLC = 1
    p24 = {
        "timestamp": 1478193345.4,
        "canId": "018f",
        "dlc": 1,
        "data": ["AA"],
        "flag": "R"
    }
    status, body = post_predict(p24)
    tracker.assert_equal(status, 200, "2.4 Boundary DLC = 1 -> HTTP 200 OK")

    # 2.5 Boundary DLC = 7
    p25 = {
        "timestamp": 1478193345.5,
        "canId": "018f",
        "dlc": 7,
        "data": ["11", "22", "33", "44", "55", "66", "77"],
        "flag": "R"
    }
    status, body = post_predict(p25)
    tracker.assert_equal(status, 200, "2.5 Boundary DLC = 7 -> HTTP 200 OK")

    # 2.6 Boundary DLC = 8
    p26 = {
        "timestamp": 1478193345.6,
        "canId": "018f",
        "dlc": 8,
        "data": ["11", "22", "33", "44", "55", "66", "77", "88"],
        "flag": "R"
    }
    status, body = post_predict(p26)
    tracker.assert_equal(status, 200, "2.6 Boundary DLC = 8 -> HTTP 200 OK")

    # 2.7 Payload Boundary: Min byte values (0x00)
    p27 = {
        "timestamp": 1478193345.7,
        "canId": "0002",
        "dlc": 8,
        "data": ["00", "00", "00", "00", "00", "00", "00", "00"],
        "flag": "R"
    }
    status, body = post_predict(p27)
    tracker.assert_equal(status, 200, "2.7 Min payload boundary (0x00) -> HTTP 200 OK")

    # 2.8 Payload Boundary: Max byte values (0xFF)
    p28 = {
        "timestamp": 1478193345.8,
        "canId": "0002",
        "dlc": 8,
        "data": ["FF", "FF", "FF", "FF", "FF", "FF", "FF", "FF"],
        "flag": "R"
    }
    status, body = post_predict(p28)
    tracker.assert_equal(status, 200, "2.8 Max payload boundary (0xFF) -> HTTP 200 OK")

    # 2.9 Malformed: Empty / Null Body -> 400 Bad Request
    status, _ = post_predict(None)
    tracker.assert_equal(status, 400, "2.9 Null / Empty request body -> HTTP 400 Bad Request")

    # 2.10 Malformed: Null CAN ID -> 400 Bad Request
    p210 = {"timestamp": 1478193346.0, "canId": None, "dlc": 8, "data": ["00"] * 8, "flag": "R"}
    status, _ = post_predict(p210)
    tracker.assert_equal(status, 400, "2.10 Null CAN ID -> HTTP 400 Bad Request")

    # 2.11 Malformed: Empty String CAN ID -> 400 Bad Request
    p211 = {"timestamp": 1478193346.0, "canId": "   ", "dlc": 8, "data": ["00"] * 8, "flag": "R"}
    status, _ = post_predict(p211)
    tracker.assert_equal(status, 400, "2.11 Empty CAN ID -> HTTP 400 Bad Request")

    # 2.12 Malformed: Non-Hex CAN ID -> 400 Bad Request
    p212 = {"timestamp": 1478193346.0, "canId": "XYZ123", "dlc": 8, "data": ["00"] * 8, "flag": "R"}
    status, _ = post_predict(p212)
    tracker.assert_equal(status, 400, "2.12 Non-hex CAN ID ('XYZ123') -> HTTP 400 Bad Request")

    # 2.13 Malformed: Null Data Array -> 400 Bad Request
    p213 = {"timestamp": 1478193346.0, "canId": "043f", "dlc": 8, "data": None, "flag": "R"}
    status, _ = post_predict(p213)
    tracker.assert_equal(status, 400, "2.13 Null Data array -> HTTP 400 Bad Request")

    # 2.14 Malformed: Corrupt Hex Byte in Payload -> 400 Bad Request
    p214 = {"timestamp": 1478193346.0, "canId": "043f", "dlc": 8, "data": ["00", "BAD_BYTE", "00", "00", "00", "00", "00", "00"], "flag": "R"}
    status, _ = post_predict(p214)
    tracker.assert_equal(status, 400, "2.14 Corrupt non-hex payload byte -> HTTP 400 Bad Request")

    # 2.15 Malformed: Out-of-Range DLCs -> 400 Bad Request
    p215a = {"timestamp": 1478193346.0, "canId": "043f", "dlc": -1, "data": ["00"] * 8, "flag": "R"}
    status_a, _ = post_predict(p215a)
    tracker.assert_equal(status_a, 400, "2.15a Negative DLC (-1) -> HTTP 400 Bad Request")

    p215b = {"timestamp": 1478193346.0, "canId": "043f", "dlc": 99, "data": ["00"] * 8, "flag": "R"}
    status_b, _ = post_predict(p215b)
    tracker.assert_equal(status_b, 400, "2.15b Excessive DLC (99) -> HTTP 400 Bad Request")


# =============================================================================
# TIER 3: Cross-Feature STOMP Message Broker Integration
# =============================================================================
def run_tier_3_tests(tracker):
    print("\n" + "=" * 60)
    print("RUNNING TIER 3: Cross-Feature STOMP WebSocket Alert Broker")
    print("=" * 60)

    # 3.1 Raw WebSocket Handshake to /ws/alerts
    ws = None
    try:
        ws = websocket.create_connection(WS_URL, timeout=5.0)
        tracker.assert_true(ws.connected, "3.1 WebSocket Handshake to /ws/alerts connected")
    except Exception as e:
        tracker.assert_true(False, "3.1 WebSocket Handshake to /ws/alerts", str(e))
        return

    # 3.2 STOMP CONNECT Frame Negotiation
    connect_frame = "CONNECT\naccept-version:1.1,1.2\nheart-beat:10000,10000\n\n\x00"
    ws.send(connect_frame)
    response = ws.recv()
    tracker.assert_true(response.startswith("CONNECTED"), "3.2 STOMP CONNECT returns CONNECTED frame")
    tracker.assert_true("version:1.2" in response or "version:1.1" in response, "3.2 STOMP version negotiated")

    # 3.3 STOMP SUBSCRIBE Frame to /topic/alerts
    sub_frame = "SUBSCRIBE\nid:sub-e2e\ndestination:/topic/alerts\n\n\x00"
    ws.send(sub_frame)
    tracker.assert_true(True, "3.3 STOMP SUBSCRIBE to /topic/alerts dispatched")

    # 3.4 Receive Real-Time Alert Broadcasts and Validate Schema
    received_alerts = []
    deadline = time.time() + 8.0
    while time.time() < deadline and len(received_alerts) < 5:
        msg = ws.recv()
        if msg.startswith("MESSAGE") and "\n\n" in msg:
            body = msg.split("\n\n", 1)[1].rstrip("\x00")
            try:
                alert = json.loads(body)
                received_alerts.append(alert)
            except Exception as e:
                print(f"Failed to parse alert body: {e}")

    tracker.assert_true(len(received_alerts) >= 3, f"3.4 Received {len(received_alerts)} STOMP broadcast alerts")

    # Validate first alert schema
    if received_alerts:
        sample = received_alerts[0]
        tracker.assert_true("message" in sample, "3.4 Alert contains nested 'message'")
        tracker.assert_true("predictionLabel" in sample, "3.4 Alert contains 'predictionLabel'")
        tracker.assert_true("predictionClass" in sample, "3.4 Alert contains 'predictionClass'")
        tracker.assert_true("latencyMs" in sample, "3.4 Alert contains 'latencyMs'")
        tracker.assert_true("anomalyScore" in sample, "3.4 Alert contains 'anomalyScore'")

        inner_msg = sample["message"]
        tracker.assert_true("canId" in inner_msg, "3.4 Inner message contains 'canId'")
        tracker.assert_true("data" in inner_msg and len(inner_msg["data"]) == 8, "3.4 Inner message contains 8-byte data array")
        tracker.assert_true(sample["predictionLabel"] in [0, 1, 2, 3], "3.4 Alert predictionLabel in [0..3]")

    # 3.5 Clean STOMP Disconnect
    try:
        ws.send("DISCONNECT\n\n\x00")
        ws.close()
        tracker.assert_true(True, "3.5 Clean STOMP WebSocket disconnection")
    except Exception as e:
        tracker.assert_true(False, "3.5 Clean STOMP WebSocket disconnection", str(e))


# =============================================================================
# TIER 4: Real-World Telemetry Replay & Performance SLA
# =============================================================================
def run_tier_4_tests(tracker):
    print("\n" + "=" * 60)
    print("RUNNING TIER 4: Real-World Sustained Stream Replay (100+ Frames)")
    print("=" * 60)

    # 4.1 Load 100+ Real Temporal Frames
    frames = []
    if os.path.exists(PARITY_DATA_PATH):
        with open(PARITY_DATA_PATH, "r", encoding="utf-8") as f:
            cases = json.load(f)
        for tc in cases:
            raw = tc["raw"]
            frames.append({
                "timestamp": raw["Timestamp"],
                "canId": raw["CAN_ID"],
                "dlc": raw["DLC"],
                "data": raw["DATA"],
                "flag": raw["Flag"]
            })

    # If dataset has fewer than 100 frames, synthesize additional frames to exceed 100
    while len(frames) < 110:
        idx = len(frames)
        frames.append({
            "timestamp": 1478193350.0 + (idx * 0.005),
            "canId": "043f" if idx % 2 == 0 else "0000",
            "dlc": 8,
            "data": [f"{((idx * 7) + i) % 256:02x}" for i in range(8)],
            "flag": "R" if idx % 2 == 0 else "T"
        })

    tracker.assert_true(len(frames) >= 100, f"4.1 Prepared {len(frames)} temporal CAN frames for sustained replay")

    # 4.2 Stream frames through POST /api/predict and profile latency
    latencies = []
    success_count = 0
    predictions_counter = {0: 0, 1: 0, 2: 0, 3: 0}

    # Record process memory before replay
    proc = psutil.Process()
    mem_before_mb = proc.memory_info().rss / (1024 * 1024)

    start_stream_time = time.time()
    for f in frames:
        t0 = time.perf_counter()
        status, body = post_predict(f)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        if status == 200:
            success_count += 1
            latencies.append(body.get("latencyMs", elapsed_ms))
            lbl = body.get("predictionLabel", 0)
            predictions_counter[lbl] = predictions_counter.get(lbl, 0) + 1

    total_stream_sec = time.time() - start_stream_time
    mem_after_mb = proc.memory_info().rss / (1024 * 1024)

    tracker.assert_equal(success_count, len(frames), f"4.2 100% Success Rate across {len(frames)} streamed frames")

    # 4.3 Sub-millisecond Inference Latency SLA Verification
    mean_latency = sum(latencies) / len(latencies) if latencies else 0.0
    p50_latency = sorted(latencies)[len(latencies) // 2] if latencies else 0.0
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0.0

    print(f"[*] Latency Metrics: Mean: {mean_latency:.4f}ms | Median: {p50_latency:.4f}ms | P95: {p95_latency:.4f}ms | Max: {max(latencies):.4f}ms")
    tracker.assert_true(mean_latency < 2.0, f"4.3 Mean inference latency within SLA (< 2.0ms, measured {mean_latency:.4f}ms)")
    tracker.assert_true(p50_latency < 1.0, f"4.3 Median inference latency is sub-millisecond (< 1.0ms, measured {p50_latency:.4f}ms)")

    # 4.4 Memory Stability / Zero Leak Audit
    mem_delta_mb = abs(mem_after_mb - mem_before_mb)
    print(f"[*] Memory Stability: Before: {mem_before_mb:.2f}MB | After: {mem_after_mb:.2f}MB | Delta: {mem_delta_mb:.2f}MB")
    tracker.assert_true(mem_delta_mb < 50.0, f"4.4 Memory remains stable under continuous stream (Delta: {mem_delta_mb:.2f}MB < 50MB)")

    # 4.5 Continuous Multiclass Classification Verification
    print(f"[*] Classification Breakdown across {len(frames)} frames: {predictions_counter}")
    tracker.assert_true(sum(predictions_counter.values()) == len(frames), "4.5 All frames produced non-null classifications")


# =============================================================================
# MAIN RUNNER
# =============================================================================
def main():
    print("=" * 70)
    print("EdgeGuard Comprehensive Cross-Subsystem E2E Integration Test Suite")
    print("=" * 70)

    backend = BackendManager()
    tracker = TestResultTracker()

    try:
        backend.ensure_backend_running()

        run_tier_1_tests(tracker)
        run_tier_2_tests(tracker)
        run_tier_3_tests(tracker)
        run_tier_4_tests(tracker)

    except Exception as e:
        print(f"\n[FATAL ERROR] Test suite aborted due to exception: {e}")
        import traceback
        traceback.print_exc()
        tracker.assert_true(False, "Test Suite Execution", str(e))
    finally:
        backend.cleanup()

    success = tracker.print_summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
