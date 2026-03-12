package com.aipass.service;

import java.util.ArrayList;
import java.util.List;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import com.aipass.dao.PriorityRouteDao;
import com.aipass.dto.PriorityRouteIntersectionDto;
import com.aipass.dto.PriorityRoutePointDto;
import com.aipass.dto.PriorityRouteRequestDto;
import com.aipass.dto.PriorityRouteResponseDto;

/*
 * ============================================================
 * PriorityRouteService
 *
 * 긴급 차량(구급차 등) 우선 경로 계산 서비스
 *
 * 역할
 * 1️⃣ 출발 교차로 조회
 * 2️⃣ 도착 교차로 조회
 * 3️⃣ 예상 도착 시간 계산 (ETA)
 * 4️⃣ 지도에 표시할 경로 좌표 생성
 * 5️⃣ 우선 제어 교차로 목록 생성
 *
 * Controller → Service → Dao → Mapper → DB
 * ============================================================
 */

@Service
public class PriorityRouteService {

    @Autowired
    private PriorityRouteDao priorityRouteDao;

    /*
     * ============================================================
     * 긴급 차량 우선 경로 계산 메인 로직
     *
     * 입력
     * - startIntersectionId
     * - endIntersectionId
     * - vehicleType
     *
     * 출력
     * - 경로 좌표 리스트
     * - ETA
     * - 우선 제어 교차로
     * ============================================================
     */
    public PriorityRouteResponseDto getPriorityRoute(PriorityRouteRequestDto requestDto) {

        // 1️⃣ 출발 교차로 조회
        PriorityRouteIntersectionDto start =
                priorityRouteDao.getIntersectionById(requestDto.getStartIntersectionId());

        // 2️⃣ 도착 교차로 조회
        PriorityRouteIntersectionDto end =
                priorityRouteDao.getIntersectionById(requestDto.getEndIntersectionId());

        // 교차로가 없으면 종료
        if (start == null || end == null) {
            return null;
        }

        PriorityRouteResponseDto responseDto = new PriorityRouteResponseDto();

        /*
         * 출발 교차로 정보 설정
         */
        responseDto.setStartIntersectionId(start.getIntersectionId());
        responseDto.setStartIntersectionName(start.getIntersectionName());
        responseDto.setStartLatitude(start.getLatitude());
        responseDto.setStartLongitude(start.getLongitude());

        /*
         * 도착 교차로 정보 설정
         */
        responseDto.setEndIntersectionId(end.getIntersectionId());
        responseDto.setEndIntersectionName(end.getIntersectionName());
        responseDto.setEndLatitude(end.getLatitude());
        responseDto.setEndLongitude(end.getLongitude());

        /*
         * 차량 종류 설정
         */
        responseDto.setVehicleType(requestDto.getVehicleType());

        /*
         * 예상 도착 시간 계산
         */
        responseDto.setEta(calculateEta(start, end));

        /*
         * 우선 제어 교차로 목록 생성
         */
        List<Long> priorityIds = new ArrayList<>();

        priorityIds.add(start.getIntersectionId());

        if (!start.getIntersectionId().equals(end.getIntersectionId())) {
            priorityIds.add(end.getIntersectionId());
        }

        responseDto.setPriorityIntersectionIds(priorityIds);
        responseDto.setPriorityCount(priorityIds.size());

        /*
         * 지도 경로 좌표 생성
         */
        responseDto.setPathPoints(buildPathPoints(start, end));

        return responseDto;
    }

    /*
     * ============================================================
     * ETA 계산
     *
     * 두 교차로 좌표 차이를 이용해 간단한 거리 계산
     * 실제 지도 API 대신 발표용 간단 로직
     * ============================================================
     */
    private String calculateEta(PriorityRouteIntersectionDto start,
                                PriorityRouteIntersectionDto end) {

        double latDiff = Math.abs(start.getLatitude() - end.getLatitude());
        double lonDiff = Math.abs(start.getLongitude() - end.getLongitude());

        double distanceScore = (latDiff + lonDiff) * 10000;

        int seconds = Math.max(12, (int) Math.round(distanceScore * 8));

        int minutes = seconds / 60;
        int remainSeconds = seconds % 60;

        if (minutes == 0) {
            return remainSeconds + "초";
        }

        return minutes + "분 " + remainSeconds + "초";
    }

    /*
     * ============================================================
     * 지도 경로 생성
     *
     * 출발 → 도착 사이를 직선 보간
     * 좌표 6개 정도 생성
     *
     * Vue에서 빨간 경로선 표시용
     * ============================================================
     */
    private List<PriorityRoutePointDto> buildPathPoints(
            PriorityRouteIntersectionDto start,
            PriorityRouteIntersectionDto end
    ) {

        List<PriorityRoutePointDto> points = new ArrayList<>();

        double startLat = start.getLatitude();
        double startLng = start.getLongitude();
        double endLat = end.getLatitude();
        double endLng = end.getLongitude();

        int steps = 6;

        for (int i = 0; i <= steps; i++) {

            double ratio = (double) i / steps;

            double lat = startLat + (endLat - startLat) * ratio;
            double lng = startLng + (endLng - startLng) * ratio;

            points.add(new PriorityRoutePointDto(lat, lng));
        }

        return points;
    }
}