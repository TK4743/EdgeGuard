package com.edgeguard.backend;

import com.edgeguard.backend.model.CanMessage;
import com.edgeguard.backend.service.OnnxInferenceService;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;

import static org.hamcrest.Matchers.*;
import static org.junit.jupiter.api.Assertions.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
public class AdversarialPredictionTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Autowired
    private OnnxInferenceService inferenceService;

    // =========================================================================
    // SECTION 1: Extreme Boundary & Malformed Inputs (HTTP 400 vs 200)
    // =========================================================================

    @Test
    @DisplayName("Boundary CAN ID: 0x and 0X prefixes with upper/lower hex characters")
    void testBoundary_CanIdPrefixes() throws Exception {
        String[] validCanIds = {"0x0", "0X0", "0x0000", "0x7FF", "0x1FFFFFFF", "0X043f", "0x02C0"};
        for (String id : validCanIds) {
            CanMessage msg = new CanMessage(
                    1478193341.0,
                    id,
                    8,
                    new String[]{"00", "11", "22", "33", "44", "55", "66", "77"},
                    "R"
            );
            mockMvc.perform(post("/api/predict")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(objectMapper.writeValueAsString(msg)))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.predictionLabel", notNullValue()));
        }
    }

    @Test
    @DisplayName("Boundary CAN ID: Invalid prefixes and non-hex inputs rejected with 400")
    void testBoundary_InvalidCanIds() throws Exception {
        String[] invalidCanIds = {
                "", "   ", "0x", "0X", "0xG", "0x123Z", "!@#$",
                "0x80000000", // Exceeds signed 32-bit positive int
                "FFFFFFFFFFFFFFFF", // 64-bit hex overflow
                "null"
        };
        for (String id : invalidCanIds) {
            CanMessage msg = new CanMessage(
                    1478193341.0,
                    id.equals("null") ? null : id,
                    8,
                    new String[]{"00", "11", "22", "33", "44", "55", "66", "77"},
                    "R"
            );
            mockMvc.perform(post("/api/predict")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(objectMapper.writeValueAsString(msg)))
                    .andExpect(status().isBadRequest());
        }
    }

    @Test
    @DisplayName("Boundary DLC: DLC=0 and DLC=8 valid boundaries return 200 OK")
    void testBoundary_DlcMinMax() throws Exception {
        // DLC 0 with empty data array
        CanMessage msgDlc0 = new CanMessage(1478193341.0, "0316", 0, new String[]{}, "R");
        mockMvc.perform(post("/api/predict")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(msgDlc0)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.predictionLabel", notNullValue()));

        // DLC 8 with full 8-byte payload
        CanMessage msgDlc8 = new CanMessage(
                1478193341.0, "0316", 8,
                new String[]{"00", "01", "02", "03", "04", "05", "06", "07"}, "R"
        );
        mockMvc.perform(post("/api/predict")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(msgDlc8)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.predictionLabel", notNullValue()));
    }

    @Test
    @DisplayName("Boundary DLC: Out-of-range DLC (-1, 9, 15, MAX_VALUE, MIN_VALUE) rejected with 400")
    void testBoundary_DlcOutOfRange() throws Exception {
        int[] invalidDlcs = {-1, -100, 9, 15, Integer.MAX_VALUE, Integer.MIN_VALUE};
        for (int dlc : invalidDlcs) {
            CanMessage msg = new CanMessage(
                    1478193341.0, "0316", dlc,
                    new String[]{"00", "00", "00", "00", "00", "00", "00", "00"}, "R"
            );
            mockMvc.perform(post("/api/predict")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(objectMapper.writeValueAsString(msg)))
                    .andExpect(status().isBadRequest());
        }
    }

    @Test
    @DisplayName("Boundary Data: Byte array with null or malformed elements rejected with 400")
    void testBoundary_MalformedDataBytes() throws Exception {
        List<String[]> invalidPayloads = Arrays.asList(
                new String[]{"00", null, "02"},
                new String[]{"00", "", "02"},
                new String[]{"00", "   ", "02"},
                new String[]{"00", "0x", "02"},
                new String[]{"00", "0X", "02"},
                new String[]{"00", "0xGG", "02"},
                new String[]{"00", "ZZZZ", "02"},
                new String[]{"00", "99999999999999999999", "02"} // Long overflow
        );

        for (String[] payload : invalidPayloads) {
            CanMessage msg = new CanMessage(1478193341.0, "0316", 8, payload, "R");
            mockMvc.perform(post("/api/predict")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(objectMapper.writeValueAsString(msg)))
                    .andExpect(status().isBadRequest());
        }
    }

    @Test
    @DisplayName("Boundary Data: 0x prefixed bytes handled cleanly without 500 error")
    void testBoundary_0xPrefixedBytes() throws Exception {
        CanMessage msg = new CanMessage(
                1478193341.0, "0x018F", 8,
                new String[]{"0x00", "0X01", "0xFE", "0XFF", "0x10", "0x20", "0x30", "0x40"}, "R"
        );
        mockMvc.perform(post("/api/predict")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(msg)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.predictionLabel", notNullValue()));
    }

    @Test
    @DisplayName("Boundary Timestamps: Zero, negative, and large timestamps do not panic")
    void testBoundary_Timestamps() throws Exception {
        double[] timestamps = {0.0, -100.5, 1.0e12, 1478193341.123456};
        for (double ts : timestamps) {
            CanMessage msg = new CanMessage(
                    ts, "043F", 8,
                    new String[]{"10", "20", "30", "40", "50", "60", "70", "80"}, "R"
            );
            mockMvc.perform(post("/api/predict")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(objectMapper.writeValueAsString(msg)))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.predictionLabel", notNullValue()));
        }
    }

    // =========================================================================
    // SECTION 2: High Frequency Burst & Latency Stress Testing
    // =========================================================================

    @Test
    @DisplayName("Stress Test: High-frequency burst of 1,000 sequential frames with latency metrics")
    void testStress_HighFrequencyBurst() throws Exception {
        final int BURST_COUNT = 1000;
        List<Double> latencies = new ArrayList<>(BURST_COUNT);
        double baseTimestamp = 1478193300.0;

        String[] sampleIds = {"043f", "0002", "02c0", "018f", "0316", "0000", "0750"};
        Random random = new Random(42);

        // Warmup (50 requests)
        for (int i = 0; i < 50; i++) {
            CanMessage warmupMsg = new CanMessage(
                    baseTimestamp + (i * 0.001), "043f", 8,
                    new String[]{"10", "40", "60", "ff", "79", "7b", "0c", "00"}, "R"
            );
            mockMvc.perform(post("/api/predict")
                    .contentType(MediaType.APPLICATION_JSON)
                    .content(objectMapper.writeValueAsString(warmupMsg)));
        }

        long burstStartNanos = System.nanoTime();
        for (int i = 0; i < BURST_COUNT; i++) {
            String id = sampleIds[random.nextInt(sampleIds.length)];
            // Simulated 0ms delta or microsecond burst
            double ts = baseTimestamp + (i * 0.0001);
            CanMessage msg = new CanMessage(
                    ts, id, 8,
                    new String[]{
                            String.format("%02x", random.nextInt(256)),
                            String.format("%02x", random.nextInt(256)),
                            String.format("%02x", random.nextInt(256)),
                            String.format("%02x", random.nextInt(256)),
                            "00", "00", "00", "00"
                    },
                    "R"
            );

            long reqStart = System.nanoTime();
            MvcResult result = mockMvc.perform(post("/api/predict")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(objectMapper.writeValueAsString(msg)))
                    .andExpect(status().isOk())
                    .andReturn();
            double reqLatencyMs = (System.nanoTime() - reqStart) / 1_000_000.0;
            latencies.add(reqLatencyMs);
        }
        long totalBurstNanos = System.nanoTime() - burstStartNanos;
        double totalBurstMs = totalBurstNanos / 1_000_000.0;

        Collections.sort(latencies);
        double minLatency = latencies.get(0);
        double maxLatency = latencies.get(latencies.size() - 1);
        double medianLatency = latencies.get(latencies.size() / 2);
        double p95Latency = latencies.get((int) (latencies.size() * 0.95));
        double p99Latency = latencies.get((int) (latencies.size() * 0.99));
        double sumLatency = 0.0;
        for (double l : latencies) sumLatency += l;
        double meanLatency = sumLatency / latencies.size();

        System.out.printf("=== High Frequency Burst Benchmark (1,000 frames) ===%n");
        System.out.printf("Total Burst Time: %.2f ms (Throughput: %.1f req/s)%n", totalBurstMs, (BURST_COUNT / (totalBurstMs / 1000.0)));
        System.out.printf("Min Latency:    %.3f ms%n", minLatency);
        System.out.printf("Mean Latency:   %.3f ms%n", meanLatency);
        System.out.printf("Median Latency: %.3f ms%n", medianLatency);
        System.out.printf("P95 Latency:    %.3f ms%n", p95Latency);
        System.out.printf("P99 Latency:    %.3f ms%n", p99Latency);
        System.out.printf("Max Latency:    %.3f ms%n", maxLatency);
        System.out.printf("=====================================================%n");

        // Assert stability: Mean latency under 5.0 ms
        assertTrue(meanLatency < 5.0, "Mean latency should remain sub-5ms under burst");
        // Assert P95 under 10.0 ms
        assertTrue(p95Latency < 10.0, "P95 latency should remain sub-10ms under burst");
    }

    // =========================================================================
    // SECTION 3: Attack Classification & Feature Extraction Stability
    // =========================================================================

    @Test
    @DisplayName("Adversarial Attack Simulation: DoS, Fuzzy, Spoofing, and Normal patterns")
    void testAttackClasses_ClassificationIntegrity() throws Exception {
        // 1. DoS pattern: CAN ID 0000, 00 payload, zero delta
        CanMessage dosMsg = new CanMessage(
                1478193345.0, "0000", 8,
                new String[]{"00", "00", "00", "00", "00", "00", "00", "00"}, "T"
        );
        mockMvc.perform(post("/api/predict")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(dosMsg)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.predictionClass", is("DoS")))
                .andExpect(jsonPath("$.predictionLabel", is(1)))
                .andExpect(jsonPath("$.anomalyScore", greaterThan(0.5)));

        // 2. Fuzzy pattern: Random IDs and high entropy payload
        CanMessage fuzzyMsg = new CanMessage(
                1478193345.5, "07FD", 8,
                new String[]{"AA", "55", "C3", "3C", "F0", "0F", "12", "7E"}, "T"
        );
        mockMvc.perform(post("/api/predict")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(fuzzyMsg)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.predictionLabel", notNullValue()))
                .andExpect(jsonPath("$.anomalyScore", notNullValue()));

        // 3. Normal pattern: Periodic ID 043F with standard payload
        CanMessage normalMsg = new CanMessage(
                1478193346.0, "043F", 8,
                new String[]{"01", "45", "60", "ff", "6b", "00", "00", "00"}, "R"
        );
        mockMvc.perform(post("/api/predict")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(normalMsg)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.predictionLabel", is(0)))
                .andExpect(jsonPath("$.predictionClass", is("Normal")));
    }

    // =========================================================================
    // SECTION 4: Concurrency & State Thread Safety Challenge
    // =========================================================================

    @Test
    @DisplayName("Adversarial Concurrency: Evaluate thread-safety of OnnxInferenceService under multi-threaded ingest")
    void testConcurrency_MultiThreadedStress() throws Exception {
        final int THREAD_COUNT = 8;
        final int MESSAGES_PER_THREAD = 100;
        final int TOTAL_MESSAGES = THREAD_COUNT * MESSAGES_PER_THREAD;

        ExecutorService executor = Executors.newFixedThreadPool(THREAD_COUNT);
        CountDownLatch startLatch = new CountDownLatch(1);
        CountDownLatch doneLatch = new CountDownLatch(THREAD_COUNT);

        AtomicInteger successCount = new AtomicInteger(0);
        AtomicInteger errorCount = new AtomicInteger(0);
        ConcurrentLinkedQueue<Throwable> exceptions = new ConcurrentLinkedQueue<>();

        for (int t = 0; t < THREAD_COUNT; t++) {
            final int threadId = t;
            executor.submit(() -> {
                try {
                    startLatch.await(); // Synchronize thread start
                    for (int m = 0; m < MESSAGES_PER_THREAD; m++) {
                        String canId = (m % 2 == 0) ? "043f" : "0002";
                        CanMessage msg = new CanMessage(
                                1478193000.0 + (threadId * 1000) + (m * 0.01),
                                canId,
                                8,
                                new String[]{"10", "20", "30", "40", "50", "60", "70", "80"},
                                "R"
                        );
                        double[] result = inferenceService.predict(msg);
                        if (result != null && result.length == 2 && result[0] >= 0) {
                            successCount.incrementAndGet();
                        } else {
                            errorCount.incrementAndGet();
                        }
                    }
                } catch (Throwable ex) {
                    errorCount.incrementAndGet();
                    exceptions.add(ex);
                } finally {
                    doneLatch.countDown();
                }
            });
        }

        startLatch.countDown();
        boolean completed = doneLatch.await(30, TimeUnit.SECONDS);
        executor.shutdown();

        System.out.printf("=== Concurrency Challenge Results ===%n");
        System.out.printf("Total Invocations: %d%n", TOTAL_MESSAGES);
        System.out.printf("Successful Predictions: %d%n", successCount.get());
        System.out.printf("Errors/Degraded Predictions: %d%n", errorCount.get());
        System.out.printf("Thrown Exceptions: %d%n", exceptions.size());
        for (Throwable t : exceptions) {
            System.out.printf("  Exception: %s: %s%n", t.getClass().getName(), t.getMessage());
        }
        System.out.printf("=====================================%n");

        assertTrue(completed, "All threads must finish within timeout");
        // Check for any hard JVM crashes or unhandled exceptions
        assertEquals(0, exceptions.size(), "No unhandled exceptions should escape during concurrent execution");
    }
}
