package com.aipass.controller;

import com.aipass.dao.TrafficMapper;
import com.aipass.dto.TrafficFlowHourDTO;
import com.aipass.dto.TrafficIntersectionDTO;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 교통 흐름 API
 *
 * <p>intersection 테이블 및 traffic_flow_log 테이블과 연동합니다.
 * DB 초기화가 필요한 경우 sqls/migration_traffic.sql 을 먼저 실행하세요.</p>
 */
@RestController
@RequestMapping("/api/traffic")
public class TrafficController {

    @Autowired
    private TrafficMapper trafficMapper;

    @GetMapping("/intersections")
    public ResponseEntity<?> getIntersections() {
        List<TrafficIntersectionDTO> list = trafficMapper.findAll();
        return ResponseEntity.ok(list);
    }

    @GetMapping("/intersections/{id}")
    public ResponseEntity<?> getIntersection(@PathVariable Long id) {
        TrafficIntersectionDTO intersection = trafficMapper.findById(id);
        if (intersection == null) {
            return ResponseEntity.status(404).body(Map.of("message", "교차로를 찾을 수 없습니다."));
        }
        return ResponseEntity.ok(intersection);
    }

    @GetMapping("/flow/{intersectionId}")
    public ResponseEntity<?> getTrafficFlow(@PathVariable Long intersectionId) {
        // traffic_flow_log 에 intersection_id 컬럼이 없으므로 최근 24시간 전체 집계를 반환합니다.
        List<TrafficFlowHourDTO> flow = trafficMapper.findFlowByHour(24);
        return ResponseEntity.ok(flow);
    }

    @GetMapping("/summary")
    public ResponseEntity<?> getSummary() {
        Map<String, Object> summary = trafficMapper.findSummary();

        // MyBatis map resultType 은 키를 소문자로 반환하므로 camelCase 키로 재매핑합니다.
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("totalIntersections", summary.getOrDefault("total_intersections", 0));
        result.put("normalCount",        summary.getOrDefault("normal_count",        0));
        result.put("cautionCount",       summary.getOrDefault("caution_count",       0));
        result.put("emergencyCount",     summary.getOrDefault("emergency_count",     0));
        result.put("avgCycleTime",       summary.getOrDefault("avg_cycle_time",      80));
        return ResponseEntity.ok(result);
    }

    @PostMapping("/intersections/{id}/signal")
    public ResponseEntity<?> updateSignal(@PathVariable Long id,
                                          @RequestBody Map<String, Integer> request) {
        Integer greenTime  = request.get("greenTime");
        Integer yellowTime = request.get("yellowTime");
        Integer redTime    = request.get("redTime");

        if (greenTime == null || yellowTime == null || redTime == null) {
            return ResponseEntity.badRequest().body(Map.of("message", "신호 시간을 모두 입력하세요."));
        }
        if (greenTime < 10 || greenTime > 120) {
            return ResponseEntity.badRequest().body(Map.of("message", "녹색 신호는 10~120초 범위여야 합니다."));
        }
        if (redTime < 10 || redTime > 120) {
            return ResponseEntity.badRequest().body(Map.of("message", "적색 신호는 10~120초 범위여야 합니다."));
        }

        trafficMapper.updateSignal(id, greenTime, yellowTime, redTime);

        TrafficIntersectionDTO updated = trafficMapper.findById(id);
        if (updated == null) {
            return ResponseEntity.status(404).body(Map.of("message", "교차로를 찾을 수 없습니다."));
        }

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("success", true);
        result.put("message", "신호 설정이 변경되었습니다.");
        result.put("data", updated);
        return ResponseEntity.ok(result);
    }
}
