package com.aipass.dto;

import java.util.List;

public class DashboardTrafficSummaryDTO {

    private Long todayCount;
    private Long yesterdayCount;
    private Double changePercent;
    private List<Long> weeklyData;

    public Long getTodayCount() { return todayCount; }
    public void setTodayCount(Long todayCount) { this.todayCount = todayCount; }

    public Long getYesterdayCount() { return yesterdayCount; }
    public void setYesterdayCount(Long yesterdayCount) { this.yesterdayCount = yesterdayCount; }

    public Double getChangePercent() { return changePercent; }
    public void setChangePercent(Double changePercent) { this.changePercent = changePercent; }

    public List<Long> getWeeklyData() { return weeklyData; }
    public void setWeeklyData(List<Long> weeklyData) { this.weeklyData = weeklyData; }
}
