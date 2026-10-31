package com.edgeguard.backend;

import com.edgeguard.backend.model.CanMessage;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import static org.hamcrest.Matchers.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
public class CanDataControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Test
    @DisplayName("POST /api/predict with valid normal CAN message returns 200 OK and expected structure")
    void testPredict_ValidNormalMessage() throws Exception {
        CanMessage msg = new CanMessage(
                1478193341.095,
                "043f",
                8,
                new String[]{"10", "40", "60", "ff", "79", "7b", "0c", "00"},
                "R"
        );

        mockMvc.perform(post("/api/predict")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(msg)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.predictionLabel", notNullValue()))
                .andExpect(jsonPath("$.predictionClass", notNullValue()))
                .andExpect(jsonPath("$.latencyMs", greaterThan(0.0)))
                .andExpect(jsonPath("$.anomalyScore", notNullValue()))
                .andExpect(jsonPath("$.message.canId", is("043f")));
    }

    @Test
    @DisplayName("POST /api/predict with 0x-prefixed hex CAN ID strips prefix and returns 200 OK")
    void testPredict_With0xPrefix() throws Exception {
        CanMessage msg = new CanMessage(
                1478193341.095,
                "0x043f",
                8,
                new String[]{"0x10", "0x40", "0x60", "0xff", "0x79", "0x7b", "0x0c", "0x00"},
                "R"
        );

        mockMvc.perform(post("/api/predict")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(msg)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.predictionLabel", notNullValue()))
                .andExpect(jsonPath("$.predictionClass", notNullValue()));
    }

    @Test
    @DisplayName("POST /api/predict with DoS attack CAN frame returns 200 OK and valid classification")
    void testPredict_DosAttackFrame() throws Exception {
        CanMessage msg = new CanMessage(
                1478193342.000,
                "0000",
                8,
                new String[]{"00", "00", "00", "00", "00", "00", "00", "00"},
                "T"
        );

        mockMvc.perform(post("/api/predict")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(msg)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.predictionLabel", notNullValue()))
                .andExpect(jsonPath("$.predictionClass", is("DoS")));
    }

    @Test
    @DisplayName("POST /api/predict with null body returns 400 Bad Request")
    void testPredict_NullBody() throws Exception {
        mockMvc.perform(post("/api/predict")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(""))
                .andExpect(status().isBadRequest());
    }

    @Test
    @DisplayName("POST /api/predict with null CAN ID returns 400 Bad Request")
    void testPredict_NullCanId() throws Exception {
        CanMessage msg = new CanMessage(
                1478193341.095,
                null,
                8,
                new String[]{"00", "00", "00", "00", "00", "00", "00", "00"},
                "R"
        );

        mockMvc.perform(post("/api/predict")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(msg)))
                .andExpect(status().isBadRequest());
    }

    @Test
    @DisplayName("POST /api/predict with invalid non-hex CAN ID returns 400 Bad Request")
    void testPredict_InvalidNonHexCanId() throws Exception {
        CanMessage msg = new CanMessage(
                1478193341.095,
                "XYZ123",
                8,
                new String[]{"00", "00", "00", "00", "00", "00", "00", "00"},
                "R"
        );

        mockMvc.perform(post("/api/predict")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(msg)))
                .andExpect(status().isBadRequest());
    }

    @Test
    @DisplayName("POST /api/predict with null data array returns 400 Bad Request")
    void testPredict_NullData() throws Exception {
        CanMessage msg = new CanMessage(
                1478193341.095,
                "0316",
                8,
                null,
                "R"
        );

        mockMvc.perform(post("/api/predict")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(msg)))
                .andExpect(status().isBadRequest());
    }

    @Test
    @DisplayName("POST /api/predict with invalid non-hex payload byte returns 400 Bad Request")
    void testPredict_InvalidNonHexPayload() throws Exception {
        CanMessage msg = new CanMessage(
                1478193341.095,
                "0316",
                8,
                new String[]{"00", "NOT_HEX", "00", "00", "00", "00", "00", "00"},
                "R"
        );

        mockMvc.perform(post("/api/predict")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(msg)))
                .andExpect(status().isBadRequest());
    }

    @Test
    @DisplayName("POST /api/predict with out-of-range DLC returns 400 Bad Request")
    void testPredict_InvalidDlcRange() throws Exception {
        CanMessage msg = new CanMessage(
                1478193341.095,
                "0316",
                99,
                new String[]{"00", "00", "00", "00", "00", "00", "00", "00"},
                "R"
        );

        mockMvc.perform(post("/api/predict")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(msg)))
                .andExpect(status().isBadRequest());
    }
}
