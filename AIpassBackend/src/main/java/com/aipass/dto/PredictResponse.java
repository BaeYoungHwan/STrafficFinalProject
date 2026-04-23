package com.aipass.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;

/**
 * FastAPI /api/v1/predict 응답 DTO.
 * FastAPI 응답: { "success": true, "data": [...], "message": "..." }
 */
public class PredictResponse {

    private boolean success;
    private List<PredictionItem> data;
    private String message;

    public PredictResponse() {}

    public boolean isSuccess() { return success; }
    public void setSuccess(boolean success) { this.success = success; }

    public List<PredictionItem> getData() { return data; }
    public void setData(List<PredictionItem> data) { this.data = data; }

    public String getMessage() { return message; }
    public void setMessage(String message) { this.message = message; }

    public static class PredictionItem {
        @JsonProperty("equipment_id")
        private Long equipmentId;

        @JsonProperty("is_anomaly")
        private Boolean isAnomaly;

        @JsonProperty("anomaly_score")
        private Double anomalyScore;

        @JsonProperty("fault_type")
        private String faultType;

        @JsonProperty("risk_level")
        private String riskLevel;

        public PredictionItem() {}

        public Long getEquipmentId() { return equipmentId; }
        public void setEquipmentId(Long equipmentId) { this.equipmentId = equipmentId; }
        public Boolean getIsAnomaly() { return isAnomaly; }
        public void setIsAnomaly(Boolean isAnomaly) { this.isAnomaly = isAnomaly; }
        public Double getAnomalyScore() { return anomalyScore; }
        public void setAnomalyScore(Double anomalyScore) { this.anomalyScore = anomalyScore; }
        public String getFaultType() { return faultType; }
        public void setFaultType(String faultType) { this.faultType = faultType; }
        public String getRiskLevel() { return riskLevel; }
        public void setRiskLevel(String riskLevel) { this.riskLevel = riskLevel; }
    }
}
