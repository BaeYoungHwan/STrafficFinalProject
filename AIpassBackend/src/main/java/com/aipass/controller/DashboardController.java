package com.aipass.controller;

import com.aipass.dao.DashboardMapper;
import com.aipass.dto.DashboardIntersectionDTO;
import com.aipass.dto.DashboardViolationSummaryDTO;
import com.aipass.dto.WeatherLogDTO;
import com.aipass.dto.RoadSegmentDTO;
import com.aipass.dto.DashboardTrafficSummaryDTO;
import com.aipass.dto.DashboardCctvStatusDTO;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/dashboard")
public class DashboardController {

    private static final Logger logger = LoggerFactory.getLogger(DashboardController.class);

    private final DashboardMapper dashboardMapper;

    public DashboardController(DashboardMapper dashboardMapper) {
        this.dashboardMapper = dashboardMapper;
    }

    /**
     * 교차로 전체 목록 조회
     * GET /api/dashboard/intersections
     */
    @GetMapping("/intersections")
    public ResponseEntity<?> getIntersections() {
        try {
            List<DashboardIntersectionDTO> data = dashboardMapper.findAllIntersections();
            return ResponseEntity.ok(Map.of("success", true, "data", data));
        } catch (Exception e) {
            logger.error("[getIntersections] 교차로 목록 조회 실패: {}", e.getMessage(), e);
            return ResponseEntity.status(500).body(Map.of("success", false, "message", "교차로 목록 조회 중 오류가 발생했습니다."));
        }
    }

    /**
     * 최신 날씨 정보 조회 (전체 최신 1건)
     * GET /api/dashboard/weather
     */
    @GetMapping("/weather")
    public ResponseEntity<?> getLatestWeather() {
        try {
            WeatherLogDTO data = dashboardMapper.findLatestWeather();
            Map<String, Object> result = new HashMap<>();
            result.put("success", true);
            result.put("data", data);
            return ResponseEntity.ok(result);
        } catch (Exception e) {
            logger.error("[getLatestWeather] 날씨 정보 조회 실패: {}", e.getMessage(), e);
            return ResponseEntity.status(500).body(Map.of("success", false, "message", "날씨 정보 조회 중 오류가 발생했습니다."));
        }
    }

    /**
     * 오늘 단속 건수 집계
     * GET /api/dashboard/today-violations
     */
    @GetMapping("/today-violations")
    public ResponseEntity<?> getTodayViolations() {
        try {
            DashboardViolationSummaryDTO data = dashboardMapper.findTodayViolationSummary();
            return ResponseEntity.ok(Map.of("success", true, "data", data));
        } catch (Exception e) {
            logger.error("[getTodayViolations] 오늘 단속 집계 조회 실패: {}", e.getMessage(), e);
            return ResponseEntity.status(500).body(Map.of("success", false, "message", "단속 집계 조회 중 오류가 발생했습니다."));
        }
    }

    /**
     * 도로 구간별 혼잡도 조회
     * GET /api/dashboard/road-congestion
     */
    @GetMapping("/road-congestion")
    public ResponseEntity<?> getRoadCongestion(
            @RequestParam(value = "direction", required = false) String direction) {
        try {
            List<RoadSegmentDTO> data;
            if (direction != null && !direction.isEmpty()) {
                data = dashboardMapper.findRoadSegmentsByDirection(direction);
            } else {
                data = dashboardMapper.findRoadSegments();
            }
            return ResponseEntity.ok(Map.of("success", true, "data", data));
        } catch (Exception e) {
            logger.error("[getRoadCongestion] 도로 혼잡도 조회 실패: {}", e.getMessage(), e);
            return ResponseEntity.status(500).body(Map.of("success", false, "message", "도로 혼잡도 조회 중 오류가 발생했습니다."));
        }
    }

    /**
     * 교통량 요약 (오늘/어제/주간) 조회
     * GET /api/dashboard/traffic-summary
     */
    @GetMapping("/traffic-summary")
    public ResponseEntity<?> getTrafficSummary() {
        try {
            DashboardTrafficSummaryDTO summary = dashboardMapper.findTrafficSummary();

            // 최근 7일 일별 교통량 (오래된 날짜 순)
            List<Long> weeklyData = new ArrayList<>();
            for (int i = 6; i >= 0; i--) {
                String date = LocalDate.now().minusDays(i).toString();
                weeklyData.add(dashboardMapper.findTrafficCountByDate(date));
            }
            summary.setWeeklyData(weeklyData);

            // 전일 대비 변화율 계산
            long today = summary.getTodayCount() != null ? summary.getTodayCount() : 0L;
            long yesterday = summary.getYesterdayCount() != null ? summary.getYesterdayCount() : 0L;
            double changePercent = yesterday > 0
                    ? (today - yesterday) / (double) yesterday * 100
                    : 0.0;
            changePercent = BigDecimal.valueOf(changePercent)
                    .setScale(1, RoundingMode.HALF_UP)
                    .doubleValue();
            summary.setChangePercent(changePercent);

            return ResponseEntity.ok(Map.of("success", true, "data", summary));
        } catch (Exception e) {
            logger.error("[getTrafficSummary] 교통량 요약 조회 실패: {}", e.getMessage(), e);
            return ResponseEntity.status(500).body(Map.of("success", false, "message", "교통량 요약 조회 중 오류가 발생했습니다."));
        }
    }

    /**
     * CCTV 상태 집계 조회
     * GET /api/dashboard/cctv-status
     */
    @GetMapping("/cctv-status")
    public ResponseEntity<?> getCctvStatus() {
        try {
            DashboardCctvStatusDTO data = dashboardMapper.findCctvStatus();
            return ResponseEntity.ok(Map.of("success", true, "data", data));
        } catch (Exception e) {
            logger.error("[getCctvStatus] CCTV 상태 조회 실패: {}", e.getMessage(), e);
            return ResponseEntity.status(500).body(Map.of("success", false, "message", "CCTV 상태 조회 중 오류가 발생했습니다."));
        }
    }
}
