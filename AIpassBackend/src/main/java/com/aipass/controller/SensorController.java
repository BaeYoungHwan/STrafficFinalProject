package com.aipass.controller;

import com.aipass.dto.PredictResponse.PredictionItem;
import com.aipass.dto.SensorIngestItemDTO;
import com.aipass.dto.SensorIngestRequest;
import com.aipass.service.PredictiveMlClient;
import com.aipass.service.SensorIngestService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.LinkedHashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/sensor")
public class SensorController {

    private static final Logger logger = LoggerFactory.getLogger(SensorController.class);
    private static final int MAX_BATCH_SIZE = 100;

    private final PredictiveMlClient mlClient;
    private final SensorIngestService sensorIngestService;

    public SensorController(PredictiveMlClient mlClient, SensorIngestService sensorIngestService) {
        this.mlClient = mlClient;
        this.sensorIngestService = sensorIngestService;
    }

    @PostMapping("/ingest")
    public ResponseEntity<Map<String, Object>> ingest(@RequestBody SensorIngestRequest request) {
        Map<String, Object> result = new LinkedHashMap<>();
        try {
            if (request == null || request.getItems() == null || request.getItems().isEmpty()) {
                result.put("success", false);
                result.put("message", "items가 비어있습니다.");
                return ResponseEntity.badRequest().body(result);
            }
            if (request.getItems().size() > MAX_BATCH_SIZE) {
                result.put("success", false);
                result.put("message", "배치 크기 상한 초과: " + request.getItems().size());
                return ResponseEntity.badRequest().body(result);
            }
            for (SensorIngestItemDTO it : request.getItems()) {
                if (!it.isValid()) {
                    result.put("success", false);
                    result.put("message", "유효하지 않은 equipmentId: " + it.getEquipmentId());
                    return ResponseEntity.badRequest().body(result);
                }
            }

            Map<Long, PredictionItem> predictions = mlClient.predict(request.getItems());
            int inserted = sensorIngestService.ingestBatch(request.getItems(), predictions);

            Map<String, Object> data = new LinkedHashMap<>();
            data.put("inserted", inserted);
            result.put("success", true);
            result.put("data", data);
            result.put("message", "센서 데이터 수신 성공");
            return ResponseEntity.ok(result);

        } catch (Exception e) {
            logger.error("[SensorController.ingest] failed: {}", e.getMessage(), e);
            result.put("success", false);
            result.put("message", "센서 데이터 처리 중 오류: " + e.getMessage());
            return ResponseEntity.status(500).body(result);
        }
    }
}
