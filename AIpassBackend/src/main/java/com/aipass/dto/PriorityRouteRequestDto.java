package com.aipass.dto;

/*
 * [PriorityRouteRequestDto]
 * 긴급 차량 우선 경로 계산을 요청할 때
 * 프론트(Vue) → 백엔드(Spring Boot)로 전달되는 요청 DTO
 *
 * 예:
 * {
 *   "startIntersectionId": 11,
 *   "endIntersectionId": 13,
 *   "vehicleType": "AMBULANCE"
 * }
 */
public class PriorityRouteRequestDto {

    // 출발 교차로 ID
    private Long startIntersectionId;

    // 도착 교차로 ID
    private Long endIntersectionId;

    // 차량 종류 (예: AMBULANCE, FIRE_TRUCK 등)
    private String vehicleType;

    public Long getStartIntersectionId() {
        return startIntersectionId;
    }

    public void setStartIntersectionId(Long startIntersectionId) {
        this.startIntersectionId = startIntersectionId;
    }

    public Long getEndIntersectionId() {
        return endIntersectionId;
    }

    public void setEndIntersectionId(Long endIntersectionId) {
        this.endIntersectionId = endIntersectionId;
    }

    public String getVehicleType() {
        return vehicleType;
    }

    public void setVehicleType(String vehicleType) {
        this.vehicleType = vehicleType;
    }
}