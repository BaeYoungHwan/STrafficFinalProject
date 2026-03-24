package com.aipass.dto;

public class DashboardViolationSummaryDTO {
    private int totalCount;
    private int speedCount;
    private int otherCount;

    public DashboardViolationSummaryDTO() {}

    public int getTotalCount() { return totalCount; }
    public void setTotalCount(int totalCount) { this.totalCount = totalCount; }

    public int getSpeedCount() { return speedCount; }
    public void setSpeedCount(int speedCount) { this.speedCount = speedCount; }

    public int getOtherCount() { return otherCount; }
    public void setOtherCount(int otherCount) { this.otherCount = otherCount; }
}
