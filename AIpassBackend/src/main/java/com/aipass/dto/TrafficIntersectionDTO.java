package com.aipass.dto;

public class TrafficIntersectionDTO {

    private Long intersectionId;
    private String name;
    private Double latitude;
    private Double longitude;
    private String congestionLevel;  // SMOOTH / SLOW / CONGESTED

    public TrafficIntersectionDTO() {}

    public Long getIntersectionId() { return intersectionId; }
    public void setIntersectionId(Long intersectionId) { this.intersectionId = intersectionId; }

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }

    public Double getLatitude() { return latitude; }
    public void setLatitude(Double latitude) { this.latitude = latitude; }

    public Double getLongitude() { return longitude; }
    public void setLongitude(Double longitude) { this.longitude = longitude; }

    public String getCongestionLevel() { return congestionLevel; }
    public void setCongestionLevel(String congestionLevel) { this.congestionLevel = congestionLevel; }

}
