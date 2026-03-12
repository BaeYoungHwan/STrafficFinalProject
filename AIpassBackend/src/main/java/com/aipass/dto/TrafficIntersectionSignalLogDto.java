package com.aipass.dto;

public class TrafficIntersectionSignalLogDto {

    private Long controlId;
    private String controlType;
    private String controlReason;
    private String createdAt;

    public Long getControlId() {
        return controlId;
    }

    public void setControlId(Long controlId) {
        this.controlId = controlId;
    }

    public String getControlType() {
        return controlType;
    }

    public void setControlType(String controlType) {
        this.controlType = controlType;
    }

    public String getControlReason() {
        return controlReason;
    }

    public void setControlReason(String controlReason) {
        this.controlReason = controlReason;
    }

    public String getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(String createdAt) {
        this.createdAt = createdAt;
    }
}