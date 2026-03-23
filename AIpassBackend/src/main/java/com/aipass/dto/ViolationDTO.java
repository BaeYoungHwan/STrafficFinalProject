package com.aipass.dto;

public class ViolationDTO {
    private Long violationId;
    private String eventId;
    private String plateNumber;
    private String violationType;
    private String imageUrl;
    private String srcImageUrl;
    private String fineStatus;   // DB: UNPROCESSED / APPROVED / REJECTED
    private Boolean isCorrected;
    private Double speedKmh;
    private String detectedAt;

    // fine_status를 한국어로 변환해서 반환
    public String getStatus() {
        if ("APPROVED".equals(fineStatus)) return "승인";
        if ("REJECTED".equals(fineStatus)) return "반려";
        return "대기중";
    }

    public ViolationDTO() {}

    public Long getViolationId() { return violationId; }
    public void setViolationId(Long violationId) { this.violationId = violationId; }

    public String getEventId() { return eventId; }
    public void setEventId(String eventId) { this.eventId = eventId; }

    public String getPlateNumber() { return plateNumber; }
    public void setPlateNumber(String plateNumber) { this.plateNumber = plateNumber; }

    public String getViolationType() { return violationType; }
    public void setViolationType(String violationType) { this.violationType = violationType; }

    public String getImageUrl() { return imageUrl; }
    public void setImageUrl(String imageUrl) { this.imageUrl = imageUrl; }

    public String getSrcImageUrl() { return srcImageUrl; }
    public void setSrcImageUrl(String srcImageUrl) { this.srcImageUrl = srcImageUrl; }

    public String getFineStatus() { return fineStatus; }
    public void setFineStatus(String fineStatus) { this.fineStatus = fineStatus; }

    public Boolean getIsCorrected() { return isCorrected; }
    public void setIsCorrected(Boolean isCorrected) { this.isCorrected = isCorrected; }

    public Double getSpeedKmh() { return speedKmh; }
    public void setSpeedKmh(Double speedKmh) { this.speedKmh = speedKmh; }

    public String getDetectedAt() { return detectedAt; }
    public void setDetectedAt(String detectedAt) { this.detectedAt = detectedAt; }
}
