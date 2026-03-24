package com.aipass.dto;

import java.time.LocalDateTime;

public class CctvInfoDTO {
    private String cctvId;
    private String cctvName;
    private String roadName;
    private Double latitude;
    private Double longitude;
    private String streamUrl;
    private String district;
    private Boolean isActive;
    private LocalDateTime updatedAt;

    public CctvInfoDTO() {}

    public String getCctvId() { return cctvId; }
    public void setCctvId(String cctvId) { this.cctvId = cctvId; }

    public String getCctvName() { return cctvName; }
    public void setCctvName(String cctvName) { this.cctvName = cctvName; }

    public String getRoadName() { return roadName; }
    public void setRoadName(String roadName) { this.roadName = roadName; }

    public Double getLatitude() { return latitude; }
    public void setLatitude(Double latitude) { this.latitude = latitude; }

    public Double getLongitude() { return longitude; }
    public void setLongitude(Double longitude) { this.longitude = longitude; }

    public String getStreamUrl() { return streamUrl; }
    public void setStreamUrl(String streamUrl) { this.streamUrl = streamUrl; }

    public String getDistrict() { return district; }
    public void setDistrict(String district) { this.district = district; }

    public Boolean getIsActive() { return isActive; }
    public void setIsActive(Boolean isActive) { this.isActive = isActive; }

    public LocalDateTime getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(LocalDateTime updatedAt) { this.updatedAt = updatedAt; }
}
