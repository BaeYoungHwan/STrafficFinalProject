package com.aipass.dto;

public class IntersectionDTO {
    private int id;
    private String name;
    private String location;
    private String status;       // NORMAL, CAUTION, EMERGENCY
    private String congestion;   // SMOOTH, SLOW, CONGESTED
    private int currentPhase;
    private int phaseRemaining;  // 남은 시간 (초)
    private int greenTime;
    private int yellowTime;
    private int redTime;
    private int totalCycle;

    public IntersectionDTO() {}

    public IntersectionDTO(int id, String name, String location, String status, String congestion,
                           int currentPhase, int phaseRemaining, int greenTime, int yellowTime, int redTime, int totalCycle) {
        this.id = id;
        this.name = name;
        this.location = location;
        this.status = status;
        this.congestion = congestion;
        this.currentPhase = currentPhase;
        this.phaseRemaining = phaseRemaining;
        this.greenTime = greenTime;
        this.yellowTime = yellowTime;
        this.redTime = redTime;
        this.totalCycle = totalCycle;
    }

    public int getId() { return id; }
    public void setId(int id) { this.id = id; }

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }

    public String getLocation() { return location; }
    public void setLocation(String location) { this.location = location; }

    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }

    public String getCongestion() { return congestion; }
    public void setCongestion(String congestion) { this.congestion = congestion; }

    public int getCurrentPhase() { return currentPhase; }
    public void setCurrentPhase(int currentPhase) { this.currentPhase = currentPhase; }

    public int getPhaseRemaining() { return phaseRemaining; }
    public void setPhaseRemaining(int phaseRemaining) { this.phaseRemaining = phaseRemaining; }

    public int getGreenTime() { return greenTime; }
    public void setGreenTime(int greenTime) { this.greenTime = greenTime; }

    public int getYellowTime() { return yellowTime; }
    public void setYellowTime(int yellowTime) { this.yellowTime = yellowTime; }

    public int getRedTime() { return redTime; }
    public void setRedTime(int redTime) { this.redTime = redTime; }

    public int getTotalCycle() { return totalCycle; }
    public void setTotalCycle(int totalCycle) { this.totalCycle = totalCycle; }
}
