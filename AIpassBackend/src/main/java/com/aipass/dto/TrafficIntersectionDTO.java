package com.aipass.dto;

public class TrafficIntersectionDTO {

    private Long intersectionId;
    private String name;
    private Double latitude;
    private Double longitude;
    private String status;           // NORMAL / CAUTION / EMERGENCY
    private String congestionLevel;  // SMOOTH / SLOW / CONGESTED
    private int greenTime;
    private int yellowTime;
    private int redTime;

    public TrafficIntersectionDTO() {}

    public Long getIntersectionId() { return intersectionId; }
    public void setIntersectionId(Long intersectionId) { this.intersectionId = intersectionId; }

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }

    public Double getLatitude() { return latitude; }
    public void setLatitude(Double latitude) { this.latitude = latitude; }

    public Double getLongitude() { return longitude; }
    public void setLongitude(Double longitude) { this.longitude = longitude; }

    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }

    public String getCongestionLevel() { return congestionLevel; }
    public void setCongestionLevel(String congestionLevel) { this.congestionLevel = congestionLevel; }

    public int getGreenTime() { return greenTime; }
    public void setGreenTime(int greenTime) { this.greenTime = greenTime; }

    public int getYellowTime() { return yellowTime; }
    public void setYellowTime(int yellowTime) { this.yellowTime = yellowTime; }

    public int getRedTime() { return redTime; }
    public void setRedTime(int redTime) { this.redTime = redTime; }

    public int getTotalCycle() { return greenTime + yellowTime + redTime; }
}
