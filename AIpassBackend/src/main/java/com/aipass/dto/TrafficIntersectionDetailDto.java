package com.aipass.dto;

import java.util.ArrayList;
import java.util.List;

public class TrafficIntersectionDetailDto {

    private Long intersectionId;
    private String intersectionName;
    private Double latitude;
    private Double longitude;

    private Integer vehicleCount;
    private String congestionLevel;
    private String congestionRecordedAt;

    private Double temperature;
    private Double vibration;
    private Double riskScore;

    private List<TrafficIntersectionEquipmentDto> equipmentList = new ArrayList<>();
    private List<TrafficIntersectionSignalLogDto> signalLogList = new ArrayList<>();
    private List<TrafficIntersectionMaintenanceDto> maintenanceList = new ArrayList<>();

    public Long getIntersectionId() {
        return intersectionId;
    }

    public void setIntersectionId(Long intersectionId) {
        this.intersectionId = intersectionId;
    }

    public String getIntersectionName() {
        return intersectionName;
    }

    public void setIntersectionName(String intersectionName) {
        this.intersectionName = intersectionName;
    }

    public Double getLatitude() {
        return latitude;
    }

    public void setLatitude(Double latitude) {
        this.latitude = latitude;
    }

    public Double getLongitude() {
        return longitude;
    }

    public void setLongitude(Double longitude) {
        this.longitude = longitude;
    }

    public Integer getVehicleCount() {
        return vehicleCount;
    }

    public void setVehicleCount(Integer vehicleCount) {
        this.vehicleCount = vehicleCount;
    }

    public String getCongestionLevel() {
        return congestionLevel;
    }

    public void setCongestionLevel(String congestionLevel) {
        this.congestionLevel = congestionLevel;
    }

    public String getCongestionRecordedAt() {
        return congestionRecordedAt;
    }

    public void setCongestionRecordedAt(String congestionRecordedAt) {
        this.congestionRecordedAt = congestionRecordedAt;
    }

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

    public List<TrafficIntersectionEquipmentDto> getEquipmentList() {
        return equipmentList;
    }

    public void setEquipmentList(List<TrafficIntersectionEquipmentDto> equipmentList) {
        this.equipmentList = equipmentList;
    }

    public List<TrafficIntersectionSignalLogDto> getSignalLogList() {
        return signalLogList;
    }

    public void setSignalLogList(List<TrafficIntersectionSignalLogDto> signalLogList) {
        this.signalLogList = signalLogList;
    }

    public List<TrafficIntersectionMaintenanceDto> getMaintenanceList() {
        return maintenanceList;
    }

    public void setMaintenanceList(List<TrafficIntersectionMaintenanceDto> maintenanceList) {
        this.maintenanceList = maintenanceList;
    }
}