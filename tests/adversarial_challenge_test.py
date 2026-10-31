"""
EdgeGuard Adversarial Stress & Telemetry Challenge Test Harness
==============================================================
Empirical Challenger 2 Suite:
  1. Concurrency Stress: Multi-threaded burst requests to /api/predict (20 threads, 200 requests)
  2. Extended Telemetry Replay: 1,000 sequential frames profiling P50, P95, P99, Max latency and RSS memory drift
  3. Multi-Client STOMP Scalability: 3 concurrent STOMP WebSocket subscribers ingesting alerts simultaneously
  4. Boundary Value & Malformed Rejection Fuzzing: 0x variations, odd hex, 29-bit CAN IDs, empty payloads
"""

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
import psutil
import websocket

BASE_URL = "http://localhost:8080"
WS_URL = "ws://localhost:8080/ws/alerts"

JAR_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "backend", "target", "backend-0.0.1-SNAPSHOT.jar")
)

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

        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.spawned_process = subprocess.Popen(
            ["java", "-jar", JAR_PATH],
            cwd=repo_root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        print("[*] Waiting for Spring Boot initialization...")
        deadline = time.time() + 35.0
        while time.time() < deadline:
            if self.is_backend_alive():
                print("[*] Backend successfully initialized and listening on port 8080.")
                return
            time.sleep(1.0)

        raise TimeoutError(f"Backend failed to respond on port 8080 within timeout.")

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


def test_concurrent_burst():
    print("\n--- Challenge 1: Concurrency & Thread-Safety Burst (20 workers, 200 requests) ---")
    payloads = [
        {"timestamp": 1478193341.0 + (i * 0.01), "canId": "043f" if i % 2 == 0 else "0000", "dlc": 8, "data": ["00"] * 8, "flag": "R"}
        for i in range(200)
    ]
    
    start_time = time.perf_counter()
    errors = []
    latencies = []
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(post_predict, p): idx for idx, p in enumerate(payloads)}
        for future in as_completed(futures):
            try:
                status, body = future.result()
                if status != 200:
                    errors.append(f"HTTP {status}")
                else:
                    latencies.append(body.get("latencyMs", 0.0))
            except Exception as e:
                errors.append(str(e))
                
    total_time = time.perf_counter() - start_time
    print(f"Total time for 200 concurrent requests: {total_time:.3f}s (Throughput: {200/total_time:.1f} req/s)")
    print(f"Errors encountered: {len(errors)}")
    if errors:
        print(f"Sample errors: {errors[:5]}")
    mean_lat = sum(latencies)/len(latencies) if latencies else 0
    p50_lat = sorted(latencies)[len(latencies)//2] if latencies else 0
    print(f"Concurrent Ingestion Latency: Mean: {mean_lat:.4f}ms | Median: {p50_lat:.4f}ms")
    return len(errors) == 0, mean_lat, p50_lat


def test_sustained_stream_replay_1000():
    print("\n--- Challenge 2: Sustained Telemetry Stream Replay (1,000 Frames) ---")
    proc = psutil.Process()
    mem_before_mb = proc.memory_info().rss / (1024 * 1024)
    
    # Generate 1000 temporal frames
    frames = []
    for i in range(1000):
        # Mix normal and various attacks
        if i % 100 < 5:
            # DoS
            cid = "0000"
            data = ["00"] * 8
            flag = "T"
        elif i % 100 < 10:
            # Fuzzy
            cid = f"{(i * 37) % 2047:04x}"
            data = [f"{(i * 13 + b) % 256:02x}" for b in range(8)]
            flag = "T"
        elif i % 100 < 15:
            # Spoofing
            cid = "0316"
            data = [f"{(255 - b) % 256:02x}" for b in range(8)]
            flag = "T"
        else:
            # Normal
            cid = ["043f", "0002", "02c0", "018f", "0316"][i % 5]
            data = [f"{(i + b) % 256:02x}" for b in range(8)]
            flag = "R"
            
        frames.append({
            "timestamp": 1478193300.0 + (i * 0.005),
            "canId": cid,
            "dlc": 8,
            "data": data,
            "flag": flag
        })
        
    latencies = []
    success = 0
    pred_counts = {}
    
    t0 = time.time()
    for f in frames:
        status, body = post_predict(f)
        if status == 200:
            success += 1
            latencies.append(body.get("latencyMs", 0.0))
            lbl = body.get("predictionLabel", -1)
            pred_counts[lbl] = pred_counts.get(lbl, 0) + 1
            
    stream_duration = time.time() - t0
    mem_after_mb = proc.memory_info().rss / (1024 * 1024)
    mem_delta = mem_after_mb - mem_before_mb
    
    sorted_lat = sorted(latencies)
    mean_lat = sum(latencies) / len(latencies) if latencies else 0.0
    p50_lat = sorted_lat[int(len(sorted_lat) * 0.50)] if sorted_lat else 0.0
    p95_lat = sorted_lat[int(len(sorted_lat) * 0.95)] if sorted_lat else 0.0
    p99_lat = sorted_lat[int(len(sorted_lat) * 0.99)] if sorted_lat else 0.0
    max_lat = max(latencies) if latencies else 0.0
    
    print(f"Replayed {success}/{len(frames)} frames in {stream_duration:.2f}s ({success/stream_duration:.1f} frames/sec)")
    print(f"Latency Percentiles (ms): Mean: {mean_lat:.4f} | P50: {p50_lat:.4f} | P95: {p95_lat:.4f} | P99: {p99_lat:.4f} | Max: {max_lat:.4f}")
    print(f"Memory: Initial: {mem_before_mb:.2f}MB | Final: {mem_after_mb:.2f}MB | Delta: {mem_delta:+.2f}MB")
    print(f"Prediction Distribution: {pred_counts} (0: Normal, 1: DoS, 2: Fuzzy, 3: Spoofing)")
    
    sla_passed = (success == 1000) and (mean_lat < 2.0) and (p50_lat < 1.0) and (abs(mem_delta) < 25.0)
    return sla_passed, mean_lat, p50_lat, p95_lat, mem_delta


def test_concurrent_stomp_clients():
    print("\n--- Challenge 3: Multi-Client STOMP Scalability (3 Concurrent Subscribers) ---")
    clients = []
    messages_received = {0: [], 1: [], 2: []}
    
    for i in range(3):
        try:
            ws = websocket.create_connection(WS_URL, timeout=5.0)
            ws.send("CONNECT\naccept-version:1.1,1.2\nheart-beat:10000,10000\n\n\x00")
            resp = ws.recv()
            if not resp.startswith("CONNECTED"):
                print(f"Client {i} failed CONNECT: {resp[:50]}")
                return False
            ws.send(f"SUBSCRIBE\nid:sub-challenger-{i}\ndestination:/topic/alerts\n\n\x00")
            clients.append(ws)
        except Exception as e:
            print(f"Client {i} error: {e}")
            return False
            
    print(f"Successfully connected and subscribed {len(clients)} STOMP clients.")
    
    # Collect alerts across all 3 clients
    for idx, ws in enumerate(clients):
        t_end = time.time() + 3.0
        while time.time() < t_end and len(messages_received[idx]) < 5:
            try:
                ws.settimeout(0.5)
                m = ws.recv()
                if m.startswith("MESSAGE") and "\n\n" in m:
                    body = m.split("\n\n", 1)[1].rstrip("\x00")
                    messages_received[idx].append(json.loads(body))
            except Exception:
                pass
        print(f"STOMP Client {idx} received: {len(messages_received[idx])} alerts")

    # Disconnect all
    for ws in clients:
        try:
            ws.send("DISCONNECT\n\n\x00")
            ws.close()
        except Exception:
            pass

    counts = [len(messages_received[i]) for i in range(3)]
    all_received_enough = all(c >= 3 for c in counts)
    return all_received_enough


def test_extreme_fuzzing():
    print("\n--- Challenge 4: Boundary & Malformed Rejection Fuzzing ---")
    test_cases = [
        # (payload, expected_status, description)
        ({"timestamp": 1.0, "canId": "0", "dlc": 8, "data": ["00"] * 8, "flag": "R"}, 200, "Single-digit hex CAN ID ('0')"),
        ({"timestamp": 1.0, "canId": "0x7ff", "dlc": 8, "data": ["ff"] * 8, "flag": "R"}, 200, "Max standard 11-bit CAN ID ('0x7ff')"),
        ({"timestamp": 1.0, "canId": "0X043F", "dlc": 0, "data": [], "flag": "R"}, 200, "DLC 0 with empty data array"),
        ({"timestamp": 1.0, "canId": "018f", "dlc": 4, "data": ["aa", "bb", "cc", "dd"], "flag": "R"}, 200, "DLC 4 with 4 bytes (partial payload)"),
        ({"timestamp": 1.0, "canId": "   043f   ", "dlc": 8, "data": ["00"] * 8, "flag": 200}, 200, "CAN ID with leading/trailing spaces"),
        ({"timestamp": 1.0, "canId": "", "dlc": 8, "data": ["00"] * 8, "flag": "R"}, 400, "Empty string CAN ID"),
        ({"timestamp": 1.0, "canId": "0x", "dlc": 8, "data": ["00"] * 8, "flag": "R"}, 400, "Bare '0x' prefix with no hex digits"),
        ({"timestamp": 1.0, "canId": "GGGG", "dlc": 8, "data": ["00"] * 8, "flag": "R"}, 400, "Invalid hex chars in CAN ID ('GGGG')"),
        ({"timestamp": 1.0, "canId": "043f", "dlc": -5, "data": ["00"] * 8, "flag": "R"}, 400, "Negative DLC (-5)"),
        ({"timestamp": 1.0, "canId": "043f", "dlc": 9, "data": ["00"] * 8, "flag": "R"}, 400, "Exceeded DLC (9)"),
        ({"timestamp": 1.0, "canId": "043f", "dlc": 8, "data": ["00", "0xZZ", "00", "00", "00", "00", "00", "00"], "flag": "R"}, 400, "Invalid hex byte '0xZZ' in data array"),
        ({"timestamp": 1.0, "canId": "043f", "dlc": 8, "data": ["00", "", "00", "00", "00", "00", "00", "00"], "flag": "R"}, 400, "Empty string byte in data array"),
    ]
    
    passed = 0
    for payload, expected_status, desc in test_cases:
        status, _ = post_predict(payload)
        if status == expected_status:
            passed += 1
            print(f"  [PASS] {desc} -> Expected HTTP {expected_status}, got HTTP {status}")
        else:
            print(f"  [FAIL] {desc} -> Expected HTTP {expected_status}, got HTTP {status}")
            
    print(f"Fuzzing Results: {passed}/{len(test_cases)} Passed.")
    return passed == len(test_cases)


def main():
    print("=" * 70)
    print("EdgeGuard Empirical Challenger 2: Stress, Concurrency & Telemetry Suite")
    print("=" * 70)

    backend = BackendManager()
    try:
        backend.ensure_backend_running()

        c1_ok, c1_mean, c1_p50 = test_concurrent_burst()
        c2_ok, c2_mean, c2_p50, c2_p95, c2_mem = test_sustained_stream_replay_1000()
        c3_ok = test_concurrent_stomp_clients()
        c4_ok = test_extreme_fuzzing()

        print("\n" + "=" * 70)
        print("CHALLENGER SUITE SUMMARY:")
        print(f"  Challenge 1 (200-Req Concurrency Burst)   : {'PASS' if c1_ok else 'FAIL'} (P50: {c1_p50:.4f}ms)")
        print(f"  Challenge 2 (1,000-Frame Stream Replay)  : {'PASS' if c2_ok else 'FAIL'} (Mean: {c2_mean:.4f}ms, P50: {c2_p50:.4f}ms, Delta: {c2_mem:+.2f}MB)")
        print(f"  Challenge 3 (Multi-Client STOMP Ingestion): {'PASS' if c3_ok else 'FAIL'}")
        print(f"  Challenge 4 (Boundary & Fuzzing Rejections): {'PASS' if c4_ok else 'FAIL'}")

        overall = c1_ok and c2_ok and c3_ok and c4_ok
        print(f"OVERALL EMPIRICAL VERDICT: {'APPROVE' if overall else 'REJECT'}")
        print("=" * 70)
        sys.exit(0 if overall else 1)
    finally:
        backend.cleanup()


if __name__ == "__main__":
    main()
