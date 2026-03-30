package com.aipass.dto;

public class TrafficFlowHourDTO {

    private String hour;             // "06:00" 형식
    private int vehicleCount;
    private Double avgSpeed;
    private String congestionLevel;  // SMOOTH / SLOW / CONGESTED

    public TrafficFlowHourDTO() {}

    public String getHour() { return hour; }
    public void setHour(String hour) { this.hour = hour; }

    public int getVehicleCount() { return vehicleCount; }
    public void setVehicleCount(int vehicleCount) { this.vehicleCount = vehicleCount; }

    public Double getAvgSpeed() { return avgSpeed; }
    public void setAvgSpeed(Double avgSpeed) { this.avgSpeed = avgSpeed; }

    public String getCongestionLevel() { return congestionLevel; }
    public void setCongestionLevel(String congestionLevel) { this.congestionLevel = congestionLevel; }
}
