package com.aipass.dto;

import java.util.ArrayList;
import java.util.List;

/*
 * [PriorityRouteResponseDto]
 * 긴급 차량 우선 경로 계산 결과를 프론트(Vue)에 전달하는 DTO
 *
 * 주요 데이터:
 * - 출발 교차로 정보
 * - 도착 교차로 정보
 * - 예상 도착 시간 (ETA)
 * - 우선 제어 교차로 목록
 * - 지도 경로 좌표 리스트
 */
public class PriorityRouteResponseDto {

    private Long startIntersectionId;
    private String startIntersectionName;
    private Double startLatitude;
    private Double startLongitude;

    private Long endIntersectionId;
    private String endIntersectionName;
    private Double endLatitude;
    private Double endLongitude;

    private String vehicleType;

    // 예상 도착 시간
    private String eta;

    // 우선 제어 교차로 개수
    private Integer priorityCount;

    // 우선 제어 교차로 ID 목록
    private List<Long> priorityIntersectionIds = new ArrayList<>();

    // 지도에 표시할 경로 좌표
    private List<PriorityRoutePointDto> pathPoints = new ArrayList<>();

    /* Getter / Setter */

    public Long getStartIntersectionId() { return startIntersectionId; }
    public void setStartIntersectionId(Long startIntersectionId) { this.startIntersectionId = startIntersectionId; }

    public String getStartIntersectionName() { return startIntersectionName; }
    public void setStartIntersectionName(String startIntersectionName) { this.startIntersectionName = startIntersectionName; }

    public Double getStartLatitude() { return startLatitude; }
    public void setStartLatitude(Double startLatitude) { this.startLatitude = startLatitude; }

    public Double getStartLongitude() { return startLongitude; }
    public void setStartLongitude(Double startLongitude) { this.startLongitude = startLongitude; }

    public Long getEndIntersectionId() { return endIntersectionId; }
    public void setEndIntersectionId(Long endIntersectionId) { this.endIntersectionId = endIntersectionId; }

    public String getEndIntersectionName() { return endIntersectionName; }
    public void setEndIntersectionName(String endIntersectionName) { this.endIntersectionName = endIntersectionName; }

    public Double getEndLatitude() { return endLatitude; }
    public void setEndLatitude(Double endLatitude) { this.endLatitude = endLatitude; }

    public Double getEndLongitude() { return endLongitude; }
    public void setEndLongitude(Double endLongitude) { this.endLongitude = endLongitude; }

    public String getVehicleType() { return vehicleType; }
    public void setVehicleType(String vehicleType) { this.vehicleType = vehicleType; }

    public String getEta() { return eta; }
    public void setEta(String eta) { this.eta = eta; }

    public Integer getPriorityCount() { return priorityCount; }
    public void setPriorityCount(Integer priorityCount) { this.priorityCount = priorityCount; }

    public List<Long> getPriorityIntersectionIds() { return priorityIntersectionIds; }
    public void setPriorityIntersectionIds(List<Long> priorityIntersectionIds) { this.priorityIntersectionIds = priorityIntersectionIds; }

    public List<PriorityRoutePointDto> getPathPoints() { return pathPoints; }
    public void setPathPoints(List<PriorityRoutePointDto> pathPoints) { this.pathPoints = pathPoints; }
}