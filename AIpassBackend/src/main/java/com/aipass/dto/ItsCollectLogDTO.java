package com.aipass.dto;

import java.time.LocalDateTime;

public class ItsCollectLogDTO {
    private Long logId;
    private String collectType;
    private String status;
    private Integer totalCount;
    private Integer newCount;
    private String errorMessage;
    private LocalDateTime executedAt;

    public ItsCollectLogDTO() {}

    public ItsCollectLogDTO(String collectType, String status, Integer totalCount, Integer newCount) {
        this.collectType = collectType;
        this.status = status;
        this.totalCount = totalCount;
        this.newCount = newCount;
    }

    public Long getLogId() { return logId; }
    public void setLogId(Long logId) { this.logId = logId; }

    public String getCollectType() { return collectType; }
    public void setCollectType(String collectType) { this.collectType = collectType; }

    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }

    public Integer getTotalCount() { return totalCount; }
    public void setTotalCount(Integer totalCount) { this.totalCount = totalCount; }

    public Integer getNewCount() { return newCount; }
    public void setNewCount(Integer newCount) { this.newCount = newCount; }

    public String getErrorMessage() { return errorMessage; }
    public void setErrorMessage(String errorMessage) { this.errorMessage = errorMessage; }

    public LocalDateTime getExecutedAt() { return executedAt; }
    public void setExecutedAt(LocalDateTime executedAt) { this.executedAt = executedAt; }
}
