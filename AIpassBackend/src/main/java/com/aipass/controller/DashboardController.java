package com.aipass.controller;

import com.aipass.dao.DashboardMapper;
import com.aipass.dto.DashboardIntersectionDTO;
import com.aipass.dto.DashboardViolationSummaryDTO;
import com.aipass.dto.WeatherLogDTO;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

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
}
