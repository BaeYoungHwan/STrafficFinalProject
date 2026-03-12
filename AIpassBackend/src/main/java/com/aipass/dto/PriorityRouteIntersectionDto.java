package com.aipass.dto;

/*
 * [PriorityRouteIntersectionDto]
 * DB의 intersection 테이블에서 조회한 교차로 기본 정보를 담는 DTO
 *
 * intersection 테이블 컬럼:
 * intersection_id
 * name
 * latitude
 * longitude
 */
public class PriorityRouteIntersectionDto {

    private Long intersectionId;
    private String intersectionName;
    private Double latitude;
    private Double longitude;

    public Long getIntersectionId() {
        return intersectionId;
    }

    public void setIntersectionId(Long intersectionId) {
        this.intersectionId = intersectionId;
    }

    public String getIntersectionName() {
        return intersectionName;
    }

    public void setIntersectionName(String intersectionName) {
        this.intersectionName = intersectionName;
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