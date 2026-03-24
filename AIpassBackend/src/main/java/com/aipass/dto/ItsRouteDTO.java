package com.aipass.dto;

import java.time.LocalDateTime;

public class ItsRouteDTO {
    private Long routeId;
    private String routeNo;
    private String routeName;
    private Boolean collectUp;
    private Boolean collectDown;
    private Boolean isActive;
    private String memo;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

    public ItsRouteDTO() {}

    public Long getRouteId() { return routeId; }
    public void setRouteId(Long routeId) { this.routeId = routeId; }

    public String getRouteNo() { return routeNo; }
    public void setRouteNo(String routeNo) { this.routeNo = routeNo; }

    public String getRouteName() { return routeName; }
    public void setRouteName(String routeName) { this.routeName = routeName; }

    public Boolean getCollectUp() { return collectUp; }
    public void setCollectUp(Boolean collectUp) { this.collectUp = collectUp; }

    public Boolean getCollectDown() { return collectDown; }
    public void setCollectDown(Boolean collectDown) { this.collectDown = collectDown; }

    public Boolean getIsActive() { return isActive; }
    public void setIsActive(Boolean isActive) { this.isActive = isActive; }

    public String getMemo() { return memo; }
    public void setMemo(String memo) { this.memo = memo; }

    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }

    public LocalDateTime getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(LocalDateTime updatedAt) { this.updatedAt = updatedAt; }
}
