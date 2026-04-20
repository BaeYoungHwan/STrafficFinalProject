package com.aipass.dto;

import java.util.List;

/**
 * POST /api/sensor/ingest 요청 바디.
 * B안: raw 센서값만 수신 (ML 판정 필드 제거).
 */
public class SensorIngestRequest {
    private List<SensorIngestItemDTO> items;

    public SensorIngestRequest() {}

    public List<SensorIngestItemDTO> getItems() { return items; }
    public void setItems(List<SensorIngestItemDTO> items) { this.items = items; }
}
