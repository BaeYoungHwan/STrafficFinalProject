package com.aipass.dto;

public class TrafficMapDto {

    private Long intersectionId;
    private String name;
    private Double latitude;
    private Double longitude;
    private Integer vehicleCount;
    private String congestionLevel;
    private String latestControlType;
    private String latestControlReason;

    public TrafficMapDto() {
    }

    public Long getIntersectionId() {
        return intersectionId;
    }

    public void setIntersectionId(Long intersectionId) {
        this.intersectionId = intersectionId;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
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

    public String getLatestControlType() {
        return latestControlType;
    }

    public void setLatestControlType(String latestControlType) {
        this.latestControlType = latestControlType;
    }

    public String getLatestControlReason() {
        return latestControlReason;
    }

    public void setLatestControlReason(String latestControlReason) {
        this.latestControlReason = latestControlReason;
    }
}