package com.aipass.service;

import com.aipass.dto.PredictRequest;
import com.aipass.dto.PredictRequest.PredictRequestItem;
import com.aipass.dto.PredictResponse;
import com.aipass.dto.PredictResponse.PredictionItem;
import com.aipass.dto.SensorIngestItemDTO;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Service
public class PredictiveMlClient {

    private static final Logger logger = LoggerFactory.getLogger(PredictiveMlClient.class);

    private static final double VIB_WARN = 0.8, VIB_DANGER = 2.0;
    private static final double TEMP_WARN = 60.0, TEMP_DANGER = 80.0;
    private static final double CUR_WARN = 20.0, CUR_DANGER = 35.0;

    private final RestTemplate restTemplate;
    private final String predictUrl;
    private final String baseUrl;
    private final boolean fallbackEnabled;

    public PredictiveMlClient(
            RestTemplate restTemplate,
            @Value("${predictive.ml.base-url}") String baseUrl,
            @Value("${predictive.ml.predict-path}") String predictPath,
            @Value("${predictive.ml.fallback-enabled:true}") boolean fallbackEnabled
    ) {
        this.restTemplate = restTemplate;
        this.baseUrl = baseUrl;
        this.predictUrl = baseUrl + predictPath;
        this.fallbackEnabled = fallbackEnabled;
    }

    public Map<Long, PredictionItem> predict(List<SensorIngestItemDTO> items) {
        try {
            return callFastApi(items);
        } catch (Exception e) {
            logger.warn("[MlClient] FastAPI 호출 실패: {} — fallback 적용", e.getMessage());
            if (fallbackEnabled) return fallbackPredict(items);
            throw new RuntimeException("ML 판정 실패", e);
        }
    }

    private Map<Long, PredictionItem> callFastApi(List<SensorIngestItemDTO> items) {
        List<PredictRequestItem> reqItems = new ArrayList<>();
        for (SensorIngestItemDTO it : items) {
            reqItems.add(new PredictRequestItem(
                    it.getEquipmentId(),
                    it.getVibration() != null ? it.getVibration().doubleValue() : 0.0,
                    it.getTemperature() != null ? it.getTemperature().doubleValue() : 0.0,
                    it.getMotorCurrent() != null ? it.getMotorCurrent().doubleValue() : 0.0
            ));
        }

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        HttpEntity<PredictRequest> entity = new HttpEntity<>(new PredictRequest(reqItems), headers);

        ResponseEntity<PredictResponse> resp =
                restTemplate.exchange(predictUrl, HttpMethod.POST, entity, PredictResponse.class);

        PredictResponse body = resp.getBody();
        if (body == null || !body.isSuccess() || body.getData() == null) {
            String msg = body != null ? body.getMessage() : "null";
            throw new RuntimeException("FastAPI /predict 응답 실패: " + msg);
        }

        logger.debug("[MlClient] ML 판정 성공 — {}건", body.getData().size());
        return body.getData().stream()
                .collect(Collectors.toMap(PredictionItem::getEquipmentId, p -> p));
    }

    private Map<Long, PredictionItem> fallbackPredict(List<SensorIngestItemDTO> items) {
        logger.info("[MlClient] RULE_BASED fallback ({}건)", items.size());
        return items.stream().collect(Collectors.toMap(
                SensorIngestItemDTO::getEquipmentId,
                this::ruleJudge
        ));
    }

    private PredictionItem ruleJudge(SensorIngestItemDTO it) {
        double vib = it.getVibration() != null ? it.getVibration().doubleValue() : 0.0;
        double temp = it.getTemperature() != null ? it.getTemperature().doubleValue() : 0.0;
        double cur = it.getMotorCurrent() != null ? it.getMotorCurrent().doubleValue() : 0.0;

        int danger = (vib >= VIB_DANGER ? 1 : 0) + (temp >= TEMP_DANGER ? 1 : 0) + (cur >= CUR_DANGER ? 1 : 0);
        int warn = (vib >= VIB_WARN ? 1 : 0) + (temp >= TEMP_WARN ? 1 : 0) + (cur >= CUR_WARN ? 1 : 0) - danger;

        String risk;
        if (danger >= 2) risk = "CRITICAL";
        else if (danger == 1) risk = "HIGH";
        else if (warn >= 1) risk = "MEDIUM";
        else risk = "LOW";

        double score = Math.min(1.0, Math.max(
                Math.max(0, (vib - VIB_WARN) / (VIB_DANGER - VIB_WARN)),
                Math.max(
                        Math.max(0, (temp - TEMP_WARN) / (TEMP_DANGER - TEMP_WARN)),
                        Math.max(0, (cur - CUR_WARN) / (CUR_DANGER - CUR_WARN))
                )
        ));
        boolean anomaly = danger >= 1 || warn >= 2;

        PredictionItem pi = new PredictionItem();
        pi.setEquipmentId(it.getEquipmentId());
        pi.setIsAnomaly(anomaly);
        pi.setAnomalyScore(Math.round(score * 10000.0) / 10000.0);
        pi.setFaultType(anomaly ? "UNKNOWN" : "NORMAL");
        pi.setRiskLevel(risk);
        return pi;
    }

    public boolean resetEquipment(Long equipmentId) {
        try {
            String resetUrl = baseUrl + "/api/v1/predict/simulator/reset/" + equipmentId;
            ResponseEntity<Map> resp = restTemplate.postForEntity(resetUrl, null, Map.class);
            if (resp.getStatusCode().is2xxSuccessful() && resp.getBody() != null) {
                boolean success = Boolean.TRUE.equals(resp.getBody().get("success"));
                if (success) {
                    logger.info("[MlClient] 시뮬레이터 장비 {} 리셋 성공", equipmentId);
                }
                return success;
            }
            return false;
        } catch (Exception e) {
            logger.warn("[MlClient] 시뮬레이터 리셋 실패 eq_id={}: {}", equipmentId, e.getMessage());
            return false;
        }
    }
}
