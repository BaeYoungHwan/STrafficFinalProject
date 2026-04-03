package com.aipass.dto;

public class IntersectionDTO {
    private int id;
    private String name;
    private String location;
    private String status;       // NORMAL, CAUTION, EMERGENCY
    private String congestion;   // SMOOTH, SLOW, CONGESTED
    private int currentPhase;
    private int phaseRemaining;  // 남은 시간 (초)
    private int totalCycle;

    public IntersectionDTO() {}

    public IntersectionDTO(int id, String name, String location, String status, String congestion,
                           int currentPhase, int phaseRemaining, int totalCycle) {
        this.id = id;
        this.name = name;
        this.location = location;
        this.status = status;
        this.congestion = congestion;
        this.currentPhase = currentPhase;
        this.phaseRemaining = phaseRemaining;
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

    public int getTotalCycle() { return totalCycle; }
    public void setTotalCycle(int totalCycle) { this.totalCycle = totalCycle; }
}
