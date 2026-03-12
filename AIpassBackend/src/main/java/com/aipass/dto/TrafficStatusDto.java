package com.aipass.dto;

public class TrafficStatusDto {

    private Double temperature;
    private Double vibration;
    private Double riskScore;

    private Integer signalPercent;
    private String signalState;

    private Integer cameraPercent;
    private String cameraState;
    private String operationStatus;
    private String failureRisk;
    private String lastMaintenanceText;

    public Double getTemperature() {
        return temperature;
    }

    public void setTemperature(Double temperature) {
        this.temperature = temperature;
    }

    public Double getVibration() {
        return vibration;
    }

    public void setVibration(Double vibration) {
        this.vibration = vibration;
    }

    public Double getRiskScore() {
        return riskScore;
    }

    public void setRiskScore(Double riskScore) {
        this.riskScore = riskScore;
    }

    public Integer getSignalPercent() {
        return signalPercent;
    }

    public void setSignalPercent(Integer signalPercent) {
        this.signalPercent = signalPercent;
    }

    public String getSignalState() {
        return signalState;
    }

    public void setSignalState(String signalState) {
        this.signalState = signalState;
    }

    public Integer getCameraPercent() {
        return cameraPercent;
    }

    public void setCameraPercent(Integer cameraPercent) {
        this.cameraPercent = cameraPercent;
    }

    public String getCameraState() {
        return cameraState;
    }

    public void setCameraState(String cameraState) {
        this.cameraState = cameraState;
    }

    public String getOperationStatus() {
        return operationStatus;
    }

    public void setOperationStatus(String operationStatus) {
        this.operationStatus = operationStatus;
    }

    public String getFailureRisk() {
        return failureRisk;
    }

    public void setFailureRisk(String failureRisk) {
        this.failureRisk = failureRisk;
    }

    public String getLastMaintenanceText() {
        return lastMaintenanceText;
    }

    public void setLastMaintenanceText(String lastMaintenanceText) {
        this.lastMaintenanceText = lastMaintenanceText;
    }
}