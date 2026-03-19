package com.aipass.dto;

public class ViolationDTO {
    private Long id;
    private String eventId;
    private String plateNumber;
    private String violationType;
    private String location;
    private Double speedKmh;
    private String status;
    private String plateImageBase64;
    private String registeredAt;

    public ViolationDTO() {}

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    public String getEventId() { return eventId; }
    public void setEventId(String eventId) { this.eventId = eventId; }

    public String getPlateNumber() { return plateNumber; }
    public void setPlateNumber(String plateNumber) { this.plateNumber = plateNumber; }

    public String getViolationType() { return violationType; }
    public void setViolationType(String violationType) { this.violationType = violationType; }

    public String getLocation() { return location; }
    public void setLocation(String location) { this.location = location; }

    public Double getSpeedKmh() { return speedKmh; }
    public void setSpeedKmh(Double speedKmh) { this.speedKmh = speedKmh; }

    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }

    public String getPlateImageBase64() { return plateImageBase64; }
    public void setPlateImageBase64(String plateImageBase64) { this.plateImageBase64 = plateImageBase64; }

    public String getRegisteredAt() { return registeredAt; }
    public void setRegisteredAt(String registeredAt) { this.registeredAt = registeredAt; }
}
