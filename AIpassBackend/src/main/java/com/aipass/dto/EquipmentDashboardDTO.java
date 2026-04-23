package com.aipass.dto;

import java.math.BigDecimal;

public class EquipmentDashboardDTO {
    private Long id;
    private String name;
    private String riskLevel;
    private Integer rul;
    private String status;
    private BigDecimal motorCurrent;
    private BigDecimal vibration;
    private BigDecimal temperature;
    private Double riskScore;
    private String lastInspection;
    private String installDate;

    public EquipmentDashboardDTO() {}

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }

    public String getRiskLevel() { return riskLevel; }
    public void setRiskLevel(String riskLevel) { this.riskLevel = riskLevel; }

    public Integer getRul() { return rul; }
    public void setRul(Integer rul) { this.rul = rul; }

    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }

    public BigDecimal getMotorCurrent() { return motorCurrent; }
    public void setMotorCurrent(BigDecimal motorCurrent) { this.motorCurrent = motorCurrent; }

    public BigDecimal getVibration() { return vibration; }
    public void setVibration(BigDecimal vibration) { this.vibration = vibration; }

    public BigDecimal getTemperature() { return temperature; }
    public void setTemperature(BigDecimal temperature) { this.temperature = temperature; }

    public Double getRiskScore() { return riskScore; }
    public void setRiskScore(Double riskScore) { this.riskScore = riskScore; }

    public String getLastInspection() { return lastInspection; }
    public void setLastInspection(String lastInspection) { this.lastInspection = lastInspection; }

    public String getInstallDate() { return installDate; }
    public void setInstallDate(String installDate) { this.installDate = installDate; }
}
