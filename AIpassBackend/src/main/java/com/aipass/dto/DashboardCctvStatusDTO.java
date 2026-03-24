package com.aipass.dto;

public class DashboardCctvStatusDTO {

    private Long activeCount;
    private Long inactiveCount;
    private Long totalCount;

    public Long getActiveCount() { return activeCount; }
    public void setActiveCount(Long activeCount) { this.activeCount = activeCount; }

    public Long getInactiveCount() { return inactiveCount; }
    public void setInactiveCount(Long inactiveCount) { this.inactiveCount = inactiveCount; }

    public Long getTotalCount() { return totalCount; }
    public void setTotalCount(Long totalCount) { this.totalCount = totalCount; }
}
