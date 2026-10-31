package com.edgeguard.backend;

import com.edgeguard.backend.model.CanMessage;
import com.edgeguard.backend.service.OnnxInferenceService;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.io.File;

public class ParityTest {

    private OnnxInferenceService service;

    @BeforeEach
    void setUp() {
        service = new OnnxInferenceService();
        service.init();
    }

    @Test
    @DisplayName("Verify 100% numerical parity between Java 13-feature extraction and Python pipeline")
    void testFeatureExtractionParity() throws Exception {
        File testDataFile = new File("../ml-sidecar/parity_test_data.json");
        if (!testDataFile.exists()) {
            testDataFile = new File("ml-sidecar/parity_test_data.json");
        }
        Assertions.assertTrue(testDataFile.exists(), "parity_test_data.json must exist");

        ObjectMapper mapper = new ObjectMapper();
        JsonNode rootNode = mapper.readTree(testDataFile);

        int passed = 0;
        int evaluated = 0;

        for (JsonNode testCase : rootNode) {
            int index = testCase.get("index").asInt();
            JsonNode raw = testCase.get("raw");
            JsonNode pythonFeatures = testCase.get("features");

            CanMessage msg = new CanMessage();
            msg.setTimestamp(raw.get("Timestamp").asDouble());
            msg.setCanId(raw.get("CAN_ID").asText());
            msg.setDlc(raw.get("DLC").asInt());
            msg.setFlag(raw.get("Flag").asText());

            String[] dataBytes = new String[8];
            for (int i = 0; i < 8; i++) {
                dataBytes[i] = raw.get("DATA").get(i).asText();
            }
            msg.setData(dataBytes);

            float[] javaFeatures = service.extractFeatures(msg);
            Assertions.assertEquals(13, javaFeatures.length, "Java features array must have exactly 13 elements");

            // Evaluate the last 20 messages (after state warmup of 80 messages)
            if (index >= 80) {
                evaluated++;
                float maxDiff = 0.0f;
                for (int i = 0; i < 13; i++) {
                    float pVal = (float) pythonFeatures.get(i).asDouble();
                    float jVal = javaFeatures[i];
                    float diff = Math.abs(pVal - jVal);
                    if (diff > maxDiff) {
                        maxDiff = diff;
                    }
                    Assertions.assertTrue(
                            diff <= 1e-4f,
                            String.format("Feature %d mismatch at index %d: Python=%.6f, Java=%.6f, diff=%.6f",
                                    i, index, pVal, jVal, diff)
                    );
                }
                passed++;
            }
        }

        Assertions.assertEquals(20, evaluated, "Should evaluate exactly 20 post-warmup test cases");
        Assertions.assertEquals(20, passed, "All 20 post-warmup test cases must pass parity check");
    }

    @Test
    @DisplayName("Verify ONNX inference predict() returns valid classification and probability")
    void testPredictOutput() {
        CanMessage msg = new CanMessage(
                1478193341.095,
                "043f",
                8,
                new String[]{"10", "40", "60", "ff", "79", "7b", "0c", "00"},
                "R"
        );

        double[] prediction = service.predict(msg);
        Assertions.assertNotNull(prediction);
        Assertions.assertEquals(2, prediction.length);

        int label = (int) prediction[0];
        Assertions.assertTrue(label >= 0 && label <= 3, "Label should be in range [0, 3]");

        double anomalyScore = prediction[1];
        Assertions.assertTrue(anomalyScore >= 0.0 && anomalyScore <= 1.0, "Anomaly score must be between 0.0 and 1.0");
    }
}
