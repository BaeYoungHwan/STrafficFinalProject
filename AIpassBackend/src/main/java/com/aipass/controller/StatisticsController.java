package com.aipass.controller;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.*;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/statistics")
public class StatisticsController {

    private static final Logger logger = LoggerFactory.getLogger(StatisticsController.class);
    private final JdbcTemplate jdbc;

    public StatisticsController(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @GetMapping("/traffic/hourly")
    public ResponseEntity<Map<String, Object>> trafficHourly() {
        return query("시간대별 교통량",
                "SELECT EXTRACT(HOUR FROM collected_at)::int AS hour, " +
                "ROUND(AVG(speed)::numeric, 1) AS avg_speed, " +
                "COUNT(*) AS cnt " +
                "FROM traffic_flow_log " +
                "WHERE collected_at >= NOW() - INTERVAL '7 days' " +
                "GROUP BY 1 ORDER BY 1");
    }

    @GetMapping("/traffic/congestion")
    public ResponseEntity<Map<String, Object>> trafficCongestion() {
        return query("혼잡도 분포",
                "SELECT congestion_level AS label, COUNT(*) AS value " +
                "FROM traffic_flow_log " +
                "WHERE collected_at >= NOW() - INTERVAL '7 days' " +
                "GROUP BY 1 ORDER BY 2 DESC");
    }

    @GetMapping("/violation/daily")
    public ResponseEntity<Map<String, Object>> violationDaily() {
        return query("일별 단속 건수",
                "SELECT TO_CHAR(detected_at, 'MM.DD') AS label, COUNT(*) AS value " +
                "FROM violation_log " +
                "WHERE detected_at >= NOW() - INTERVAL '30 days' " +
                "GROUP BY 1, detected_at::date ORDER BY detected_at::date");
    }

    @GetMapping("/violation/type")
    public ResponseEntity<Map<String, Object>> violationType() {
        return query("유형별 단속",
                "SELECT violation_type AS label, COUNT(*) AS value " +
                "FROM violation_log GROUP BY 1 ORDER BY 2 DESC");
    }

    @GetMapping("/violation/intersection")
    public ResponseEntity<Map<String, Object>> violationIntersection() {
        return query("교차로별 단속",
                "SELECT COALESCE(i.name, '미지정') AS label, COUNT(*) AS value " +
                "FROM violation_log v " +
                "LEFT JOIN intersection i ON i.intersection_id = v.intersection_id " +
                "GROUP BY 1 ORDER BY 2 DESC LIMIT 10");
    }

    @GetMapping("/predictive/anomaly")
    public ResponseEntity<Map<String, Object>> predictiveAnomaly() {
        return query("장비별 이상 빈도",
                "SELECT 'CAM' || LPAD(equipment_id::text, 2, '0') AS label, " +
                "COUNT(*) AS value " +
                "FROM sensor_log WHERE is_anomaly = true " +
                "GROUP BY equipment_id ORDER BY equipment_id");
    }

    @GetMapping("/predictive/risk")
    public ResponseEntity<Map<String, Object>> predictiveRisk() {
        return query("위험도 분포",
                "SELECT COALESCE(risk_level, 'LOW') AS label, COUNT(*) AS value " +
                "FROM equipment GROUP BY 1 ORDER BY " +
                "CASE COALESCE(risk_level, 'LOW') WHEN 'LOW' THEN 1 WHEN 'MEDIUM' THEN 2 " +
                "WHEN 'HIGH' THEN 3 WHEN 'CRITICAL' THEN 4 ELSE 5 END");
    }

    @GetMapping("/predictive/operation")
    public ResponseEntity<Map<String, Object>> predictiveOperation() {
        return query("평균 운용일수",
                "SELECT ROUND(AVG(CURRENT_DATE - installation_date)) AS avg_days, " +
                "MIN(CURRENT_DATE - installation_date) AS min_days, " +
                "MAX(CURRENT_DATE - installation_date) AS max_days, " +
                "COUNT(*) AS total " +
                "FROM equipment");
    }

    @GetMapping("/weather/trend")
    public ResponseEntity<Map<String, Object>> weatherTrend() {
        return query("기온/습도 추이",
                "SELECT TO_CHAR(collected_at, 'MM.DD') AS label, " +
                "ROUND(AVG(temperature)::numeric, 1) AS avg_temp, " +
                "ROUND(AVG(humidity)::numeric, 0) AS avg_humidity " +
                "FROM weather_log " +
                "WHERE collected_at >= NOW() - INTERVAL '30 days' " +
                "GROUP BY 1, collected_at::date ORDER BY collected_at::date");
    }

    @GetMapping("/weather/current")
    public ResponseEntity<Map<String, Object>> weatherCurrent() {
        return query("현재 날씨",
                "SELECT temperature, humidity, wind_speed, sky_condition, " +
                "TO_CHAR(collected_at, 'YYYY.MM.DD HH24:MI') AS collected_at " +
                "FROM weather_log ORDER BY collected_at DESC LIMIT 1");
    }

    private ResponseEntity<Map<String, Object>> query(String label, String sql) {
        Map<String, Object> result = new LinkedHashMap<>();
        try {
            List<Map<String, Object>> data = jdbc.queryForList(sql);
            result.put("success", true);
            result.put("data", data);
            result.put("message", label + " 조회 성공");
            return ResponseEntity.ok(result);
        } catch (Exception e) {
            logger.error("[Statistics.{}] failed: {}", label, e.getMessage(), e);
            result.put("success", false);
            result.put("message", label + " 조회 실패");
            return ResponseEntity.status(500).body(result);
        }
    }
}
