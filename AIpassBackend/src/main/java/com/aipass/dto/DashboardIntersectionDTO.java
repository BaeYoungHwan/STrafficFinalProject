package com.aipass.dto;

import java.math.BigDecimal;

public class DashboardIntersectionDTO {
    private Long intersectionId;
    private String name;
    private BigDecimal latitude;
    private BigDecimal longitude;

    public DashboardIntersectionDTO() {}

    public Long getIntersectionId() { return intersectionId; }
    public void setIntersectionId(Long intersectionId) { this.intersectionId = intersectionId; }

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }

    public BigDecimal getLatitude() { return latitude; }
    public void setLatitude(BigDecimal latitude) { this.latitude = latitude; }

    public BigDecimal getLongitude() { return longitude; }
    public void setLongitude(BigDecimal longitude) { this.longitude = longitude; }
}
