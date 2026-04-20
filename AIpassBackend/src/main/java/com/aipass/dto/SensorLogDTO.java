package com.aipass.dto;

import java.math.BigDecimal;
import java.time.LocalDateTime;

public class SensorLogDTO {
    private Long logId;
    private Long equipmentId;
    private BigDecimal temperature;
    private BigDecimal vibration;
    private BigDecimal riskScore;
    private LocalDateTime recordedAt;
    private BigDecimal motorCurrent;
    private Boolean isAnomaly;
    private Double anomalyScore;
    private String faultType;
    private String riskLevel;

    public SensorLogDTO() {}

    public Long getLogId() { return logId; }
    public void setLogId(Long logId) { this.logId = logId; }

    public Long getEquipmentId() { return equipmentId; }
    public void setEquipmentId(Long equipmentId) { this.equipmentId = equipmentId; }

    public BigDecimal getTemperature() { return temperature; }
    public void setTemperature(BigDecimal temperature) { this.temperature = temperature; }

    public BigDecimal getVibration() { return vibration; }
    public void setVibration(BigDecimal vibration) { this.vibration = vibration; }

    public BigDecimal getRiskScore() { return riskScore; }
    public void setRiskScore(BigDecimal riskScore) { this.riskScore = riskScore; }

    public LocalDateTime getRecordedAt() { return recordedAt; }
    public void setRecordedAt(LocalDateTime recordedAt) { this.recordedAt = recordedAt; }

    public BigDecimal getMotorCurrent() { return motorCurrent; }
    public void setMotorCurrent(BigDecimal motorCurrent) { this.motorCurrent = motorCurrent; }

    public Boolean getIsAnomaly() { return isAnomaly; }
    public void setIsAnomaly(Boolean isAnomaly) { this.isAnomaly = isAnomaly; }

    public Double getAnomalyScore() { return anomalyScore; }
    public void setAnomalyScore(Double anomalyScore) { this.anomalyScore = anomalyScore; }

    public String getFaultType() { return faultType; }
    public void setFaultType(String faultType) { this.faultType = faultType; }

    public String getRiskLevel() { return riskLevel; }
    public void setRiskLevel(String riskLevel) { this.riskLevel = riskLevel; }
}
