package com.aipass.dto;

import java.math.BigDecimal;
import java.time.LocalDateTime;

public class SensorIngestItemDTO {

    private Long equipmentId;
    private BigDecimal vibration;
    private BigDecimal temperature;
    private BigDecimal motorCurrent;
    private LocalDateTime recordedAt;

    public SensorIngestItemDTO() {}

    public Long getEquipmentId() { return equipmentId; }
    public void setEquipmentId(Long equipmentId) { this.equipmentId = equipmentId; }

    public BigDecimal getVibration() { return vibration; }
    public void setVibration(BigDecimal vibration) { this.vibration = vibration; }

    public BigDecimal getTemperature() { return temperature; }
    public void setTemperature(BigDecimal temperature) { this.temperature = temperature; }

    public BigDecimal getMotorCurrent() { return motorCurrent; }
    public void setMotorCurrent(BigDecimal motorCurrent) { this.motorCurrent = motorCurrent; }

    public LocalDateTime getRecordedAt() { return recordedAt; }
    public void setRecordedAt(LocalDateTime recordedAt) { this.recordedAt = recordedAt; }

    public boolean isValid() {
        if (equipmentId == null || equipmentId < 1 || equipmentId > 10000) return false;
        if (vibration != null && vibration.doubleValue() > 20.0) return false;
        if (temperature != null && temperature.doubleValue() > 200.0) return false;
        if (motorCurrent != null && motorCurrent.doubleValue() > 100.0) return false;
        return true;
    }
}
