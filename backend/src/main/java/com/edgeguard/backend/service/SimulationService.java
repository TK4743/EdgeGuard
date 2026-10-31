package com.edgeguard.backend.service;

import com.edgeguard.backend.model.CanMessage;
import com.edgeguard.backend.model.PredictionResult;
import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Service;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.io.IOException;
import java.util.Arrays;
import java.util.Random;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

@Service
public class SimulationService {

    @Autowired
    private OnnxInferenceService inferenceService;

    @Autowired
    private SimpMessagingTemplate messagingTemplate;

    private ScheduledExecutorService executorService;
    private BufferedReader reader;
    private String activeDataFilePath = null;
    private Double lastTimestamp = null;

    private static final String[] NORMAL_IDS = {"043f", "0002", "02c0", "018f", "0316"};
    private final Random random = new Random();
    private double syntheticTimestamp = 0;
    private int syntheticCounter = 0;

    @PostConstruct
    public void startSimulation() {
        findAndOpenDataset();
        executorService = Executors.newSingleThreadScheduledExecutor();
        executorService.submit(this::simulationLoop);
        System.out.println("Started CAN bus simulation...");
    }

    private void findAndOpenDataset() {
        String[] preferredPaths = {
            "../data/DoS_dataset.csv",
            "data/DoS_dataset.csv",
            "../data/Fuzzy_dataset.csv",
            "data/Fuzzy_dataset.csv",
            "../data/spoofing_gear_dataset.csv",
            "data/spoofing_gear_dataset.csv"
        };
        for (String p : preferredPaths) {
            File f = new File(p);
            if (f.exists() && f.isFile()) {
                try {
                    reader = new BufferedReader(new FileReader(f));
                    activeDataFilePath = f.getAbsolutePath();
                    System.out.println("Opened CAN dataset: " + activeDataFilePath);
                    return;
                } catch (IOException e) {
                    System.err.println("Could not open " + p + ": " + e.getMessage());
                }
            }
        }

        // Scan data directories for any available CSV
        for (String dirPath : new String[]{"../data", "data"}) {
            File dir = new File(dirPath);
            if (dir.exists() && dir.isDirectory()) {
                File[] files = dir.listFiles((d, name) -> name.toLowerCase().endsWith(".csv"));
                if (files != null) {
                    for (File f : files) {
                        try {
                            reader = new BufferedReader(new FileReader(f));
                            activeDataFilePath = f.getAbsolutePath();
                            System.out.println("Opened discovered CAN dataset: " + activeDataFilePath);
                            return;
                        } catch (IOException e) {
                            // continue checking
                        }
                    }
                }
            }
        }

        reader = null;
        activeDataFilePath = null;
        syntheticTimestamp = System.currentTimeMillis() / 1000.0;
        System.out.println("No CAN dataset CSV found; activated synthetic CAN traffic fallback.");
    }

    @PreDestroy
    public void stopSimulation() {
        if (executorService != null) {
            executorService.shutdownNow();
        }
        if (reader != null) {
            try {
                reader.close();
            } catch (IOException e) {
                e.printStackTrace();
            }
        }
    }

    private void simulationLoop() {
        try {
            while (!Thread.currentThread().isInterrupted()) {
                if (reader != null) {
                    processReplayLine();
                } else {
                    processSyntheticMessage();
                }
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        } catch (Exception e) {
            System.err.println("Simulation loop exception: " + e.getMessage());
        }
    }

    private void processReplayLine() throws Exception {
        String line = reader.readLine();
        if (line == null) {
            reader.close();
            if (activeDataFilePath != null && new File(activeDataFilePath).exists()) {
                reader = new BufferedReader(new FileReader(activeDataFilePath));
                line = reader.readLine();
                lastTimestamp = null;
            } else {
                reader = null;
                return;
            }
        }

        if (line != null) {
            String[] parts = line.split(",");
            if (parts.length != 12) return;

            double timestamp = Double.parseDouble(parts[0]);
            double deltaSeconds = 0;

            if (lastTimestamp != null) {
                deltaSeconds = timestamp - lastTimestamp;
                long delayMs = (long) (deltaSeconds * 1000);

                if (delayMs < 5) delayMs = 5;
                if (delayMs > 1000) delayMs = 1000;

                long jitter = (long) (Math.random() * 20 - 10);
                long finalDelay = delayMs + jitter;
                if (finalDelay < 5) finalDelay = 5;

                Thread.sleep(finalDelay);
            }
            lastTimestamp = timestamp;

            String canId = parts[1];
            int dlc = Integer.parseInt(parts[2]);
            String[] data = new String[]{parts[3], parts[4], parts[5], parts[6], parts[7], parts[8], parts[9], parts[10]};
            String flag = parts[11];

            broadcastCanMessage(timestamp, canId, dlc, data, flag, deltaSeconds);
        }
    }

    private void processSyntheticMessage() throws Exception {
        syntheticCounter++;
        syntheticTimestamp += 0.01 + (random.nextDouble() * 0.01);

        long delayMs = 20 + random.nextInt(30);
        Thread.sleep(delayMs);

        String canId;
        int dlc = 8;
        String[] data = new String[8];
        String flag = "R";

        int attackRoll = random.nextInt(100);
        if (attackRoll < 6) {
            // DoS: ID 0000 flooded with 00 bytes
            canId = "0000";
            Arrays.fill(data, "00");
            flag = "T";
        } else if (attackRoll < 10) {
            // Fuzzy: random ID and randomized payload
            canId = String.format("%04x", random.nextInt(0x7ff));
            for (int i = 0; i < 8; i++) {
                data[i] = String.format("%02x", random.nextInt(256));
            }
            flag = "T";
        } else if (attackRoll < 13) {
            // Spoofing: typical ID with irregular payload
            canId = NORMAL_IDS[random.nextInt(NORMAL_IDS.length)];
            for (int i = 0; i < 8; i++) {
                data[i] = String.format("%02x", random.nextInt(256));
            }
            flag = "T";
        } else {
            // Normal traffic
            canId = NORMAL_IDS[syntheticCounter % NORMAL_IDS.length];
            for (int i = 0; i < 8; i++) {
                data[i] = String.format("%02x", (syntheticCounter * (i + 1)) % 256);
            }
            flag = "R";
        }

        broadcastCanMessage(syntheticTimestamp, canId, dlc, data, flag, 0.02);
    }

    private void broadcastCanMessage(double timestamp, String canId, int dlc, String[] data, String flag, double deltaSeconds) {
        CanMessage msg = new CanMessage(timestamp, canId, dlc, data, flag);

        long start = System.nanoTime();
        double[] predictionData = inferenceService.predict(msg);
        int prediction = (int) predictionData[0];
        double anomalyScore = predictionData.length > 1 ? predictionData[1] : 0.0;
        long end = System.nanoTime();

        double latencyMs = (end - start) / 1_000_000.0;

        String labelStr = switch (prediction) {
            case 0 -> "Normal";
            case 1 -> "DoS";
            case 2 -> "Fuzzy";
            case 3 -> "Spoofing";
            default -> "Unknown";
        };

        PredictionResult result = new PredictionResult(msg, prediction, labelStr, latencyMs, anomalyScore);
        messagingTemplate.convertAndSend("/topic/alerts", result);

        if (Math.random() < 0.01) {
            System.out.printf("[Replay] Timestamp: %.4f | Delta: %.4f s | Sent %s (%s)%n", timestamp, deltaSeconds, canId, labelStr);
        }
    }
}
