package com.aipass.dto;

/*
 * [PriorityRoutePointDto]
 * 긴급 차량 이동 경로를 지도에 표시하기 위한 좌표 DTO
 *
 * 예:
 * {
 *   "latitude": 37.497942,
 *   "longitude": 127.027621
 * }
 */
public class PriorityRoutePointDto {

    // 위도
    private Double latitude;

    // 경도
    private Double longitude;

    public PriorityRoutePointDto() {}

    public PriorityRoutePointDto(Double latitude, Double longitude) {
        this.latitude = latitude;
        this.longitude = longitude;
    }

    public Double getLatitude() {
        return latitude;
    }

    public void setLatitude(Double latitude) {
        this.latitude = latitude;
    }

    public Double getLongitude() {
        return longitude;
    }

    public void setLongitude(Double longitude) {
        this.longitude = longitude;
    }
}