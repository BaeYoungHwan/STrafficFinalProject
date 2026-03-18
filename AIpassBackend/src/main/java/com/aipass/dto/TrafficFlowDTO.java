package com.aipass.dto;

public class TrafficFlowDTO {
    private int intersectionId;
    private String time;
    private int volume;
    private double avgSpeed;
    private String congestion;   // SMOOTH, SLOW, CONGESTED

    public TrafficFlowDTO() {}

    public TrafficFlowDTO(int intersectionId, String time, int volume, double avgSpeed, String congestion) {
        this.intersectionId = intersectionId;
        this.time = time;
        this.volume = volume;
        this.avgSpeed = avgSpeed;
        this.congestion = congestion;
    }

    public int getIntersectionId() { return intersectionId; }
    public void setIntersectionId(int intersectionId) { this.intersectionId = intersectionId; }

    public String getTime() { return time; }
    public void setTime(String time) { this.time = time; }

    public int getVolume() { return volume; }
    public void setVolume(int volume) { this.volume = volume; }

    public double getAvgSpeed() { return avgSpeed; }
    public void setAvgSpeed(double avgSpeed) { this.avgSpeed = avgSpeed; }

    public String getCongestion() { return congestion; }
    public void setCongestion(String congestion) { this.congestion = congestion; }
}
