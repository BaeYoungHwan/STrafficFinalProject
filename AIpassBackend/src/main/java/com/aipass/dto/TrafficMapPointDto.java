package com.aipass.dto;

import java.util.ArrayList;
import java.util.List;

public class TrafficMapPointDto {

    private Long intersectionId;
    private String intersectionName;
    private Double latitude;
    private Double longitude;
    private List<TrafficMapEquipmentDto> equipmentList = new ArrayList<>();

    public TrafficMapPointDto() {
    }

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

    public List<TrafficMapEquipmentDto> getEquipmentList() {
        return equipmentList;
    }

    public void setEquipmentList(List<TrafficMapEquipmentDto> equipmentList) {
        this.equipmentList = equipmentList;
    }
}