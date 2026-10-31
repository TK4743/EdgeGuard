package com.edgeguard.backend.controller;

import com.edgeguard.backend.model.CanMessage;
import com.edgeguard.backend.model.PredictionResult;
import com.edgeguard.backend.service.OnnxInferenceService;
import org.springframework.web.bind.annotation.*;
import org.springframework.http.ResponseEntity;

@RestController
@RequestMapping("/api")
@CrossOrigin(origins = "*")
public class CanDataController {

    private final OnnxInferenceService inferenceService;

    public CanDataController(OnnxInferenceService inferenceService) {
        this.inferenceService = inferenceService;
    }

    @PostMapping("/predict")
    public ResponseEntity<PredictionResult> predict(@RequestBody(required = false) CanMessage message) {
        if (message == null) {
            return ResponseEntity.badRequest().build();
        }

        // Validate canId: must be non-null, non-empty, and valid hex
        if (message.getCanId() == null || message.getCanId().trim().isEmpty()) {
            return ResponseEntity.badRequest().build();
        }
        String rawCanId = message.getCanId().trim();
        String cleanCanId = (rawCanId.startsWith("0x") || rawCanId.startsWith("0X"))
                ? rawCanId.substring(2)
                : rawCanId;
        if (cleanCanId.isEmpty()) {
            return ResponseEntity.badRequest().build();
        }
        try {
            Integer.parseInt(cleanCanId, 16);
        } catch (NumberFormatException e) {
            return ResponseEntity.badRequest().build();
        }

        // Validate data array: must be non-null and elements must be valid hex bytes
        if (message.getData() == null) {
            return ResponseEntity.badRequest().build();
        }
        for (String byteStr : message.getData()) {
            if (byteStr == null || byteStr.trim().isEmpty()) {
                return ResponseEntity.badRequest().build();
            }
            String cleanByte = byteStr.trim();
            if (cleanByte.startsWith("0x") || cleanByte.startsWith("0X")) {
                cleanByte = cleanByte.substring(2);
            }
            try {
                Integer.parseInt(cleanByte, 16);
            } catch (NumberFormatException e) {
                return ResponseEntity.badRequest().build();
            }
        }

        // Validate dlc range [0..8]
        if (message.getDlc() < 0 || message.getDlc() > 8) {
            return ResponseEntity.badRequest().build();
        }

        try {
            long start = System.nanoTime();
            double[] res = inferenceService.predict(message);
            double latencyMs = (System.nanoTime() - start) / 1000000.0;
            String[] classes = {"Normal", "DoS", "Fuzzy", "Spoofing"};
            int label = (int) res[0];
            String className = (label >= 0 && label < 4) ? classes[label] : "Unknown";
            
            PredictionResult result = new PredictionResult(message, label, className, latencyMs, res.length > 1 ? res[1] : 0.0);
            return ResponseEntity.ok(result);
        } catch (Exception e) {
            e.printStackTrace();
            return ResponseEntity.internalServerError().build();
        }
    }
}
