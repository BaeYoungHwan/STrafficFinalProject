package com.aipass.dto;

public class SignalControlRequestDto {

    private Long intersectionId;
    private String controlType;
    private String controlReason;

    public SignalControlRequestDto() {
    }

    public Long getIntersectionId() {
        return intersectionId;
    }

    public void setIntersectionId(Long intersectionId) {
        this.intersectionId = intersectionId;
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
}