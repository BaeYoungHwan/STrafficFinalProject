package com.aipass.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;

/**
 * BE → FastAPI /api/v1/predict 요청 DTO.
 * FastAPI 기대: { "items": [{ "equipment_id":1, "vibration":0.5, "temperature":42.0, "motor_current":15.0 }] }
 */
public class PredictRequest {

    private List<PredictRequestItem> items;

    public PredictRequest() {}
    public PredictRequest(List<PredictRequestItem> items) { this.items = items; }

    public List<PredictRequestItem> getItems() { return items; }
    public void setItems(List<PredictRequestItem> items) { this.items = items; }

    public static class PredictRequestItem {
        @JsonProperty("equipment_id")
        private Long equipmentId;
        private Double vibration;
        private Double temperature;
        @JsonProperty("motor_current")
        private Double motorCurrent;

        public PredictRequestItem() {}
        public PredictRequestItem(Long equipmentId, Double vibration, Double temperature, Double motorCurrent) {
            this.equipmentId = equipmentId;
            this.vibration = vibration;
            this.temperature = temperature;
            this.motorCurrent = motorCurrent;
        }

        public Long getEquipmentId() { return equipmentId; }
        public void setEquipmentId(Long equipmentId) { this.equipmentId = equipmentId; }
        public Double getVibration() { return vibration; }
        public void setVibration(Double vibration) { this.vibration = vibration; }
        public Double getTemperature() { return temperature; }
        public void setTemperature(Double temperature) { this.temperature = temperature; }
        public Double getMotorCurrent() { return motorCurrent; }
        public void setMotorCurrent(Double motorCurrent) { this.motorCurrent = motorCurrent; }
    }
}
