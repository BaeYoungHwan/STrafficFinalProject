package com.aipass.controller;

import com.aipass.dto.IntersectionDTO;
import com.aipass.dto.TrafficFlowDTO;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 교통 흐름 API
 *
 * <p>NOTE: 현재 getDummyIntersections(), getDummyTrafficFlow() 는 하드코딩된 더미 데이터를
 * 반환합니다. DB 연동 (intersections, traffic_flow 테이블 설계) 은 추후 스프린트에서
 * 진행 예정입니다.</p>
 */
@RestController
@RequestMapping("/api/traffic")
public class TrafficController {

    // ── 더미 교차로 데이터 ──
    private List<IntersectionDTO> getDummyIntersections() {
        List<IntersectionDTO> list = new ArrayList<>();
        list.add(new IntersectionDTO(1, "세종대로 사거리",    "서울 종로구 세종대로 175",    "NORMAL",    "SMOOTH",    1, 25, 40, 5, 35, 80));
        list.add(new IntersectionDTO(2, "강남역 교차로",     "서울 강남구 강남대로 396",    "NORMAL",    "SLOW",      2, 12, 35, 5, 40, 80));
        list.add(new IntersectionDTO(3, "서초IC 교차로",     "서울 서초구 반포대로 201",    "CAUTION",   "CONGESTED", 3,  8, 30, 5, 45, 80));
        list.add(new IntersectionDTO(4, "잠실역 사거리",     "서울 송파구 올림픽로 240",    "NORMAL",    "SMOOTH",    1, 32, 45, 5, 30, 80));
        list.add(new IntersectionDTO(5, "영등포 로터리",     "서울 영등포구 영등포로 일대",   "EMERGENCY", "CONGESTED", 2,  3, 25, 5, 50, 80));
        list.add(new IntersectionDTO(6, "광화문 삼거리",     "서울 종로구 사직로 130",      "NORMAL",    "SLOW",      1, 18, 38, 5, 37, 80));
        list.add(new IntersectionDTO(7, "여의도 교차로",     "서울 영등포구 여의대로 100",   "CAUTION",   "SLOW",      3, 15, 32, 5, 43, 80));
        list.add(new IntersectionDTO(8, "용산역 사거리",     "서울 용산구 한강대로 405",    "NORMAL",    "SMOOTH",    2, 28, 42, 5, 33, 80));
        return list;
    }

    // ── 더미 교통량 시간대별 데이터 ──
    private List<TrafficFlowDTO> getDummyTrafficFlow(int intersectionId) {
        List<TrafficFlowDTO> list = new ArrayList<>();
        String[] times = {"06:00","07:00","08:00","09:00","10:00","11:00","12:00",
                          "13:00","14:00","15:00","16:00","17:00","18:00","19:00","20:00"};
        int[][] data = {
            {120, 320, 580, 510, 350, 290, 310, 280, 340, 380, 420, 560, 620, 450, 220},  // id 1
            {150, 380, 650, 590, 400, 340, 370, 330, 390, 430, 480, 630, 710, 520, 280},  // id 2
            {100, 290, 520, 470, 320, 260, 280, 250, 300, 350, 400, 510, 580, 410, 190},  // id 3
            {130, 340, 600, 540, 370, 310, 340, 300, 360, 400, 450, 580, 650, 470, 240},  // id 4
            {160, 400, 700, 640, 440, 370, 400, 360, 420, 470, 520, 680, 760, 550, 300},  // id 5
            {110, 300, 540, 480, 330, 270, 300, 260, 320, 360, 410, 530, 600, 430, 200},  // id 6
            {140, 360, 620, 560, 380, 320, 350, 310, 370, 410, 460, 600, 670, 490, 260},  // id 7
            {125, 330, 570, 500, 345, 285, 305, 275, 335, 375, 415, 550, 610, 440, 215}   // id 8
        };
        double[][] speeds = {
            {55, 45, 28, 32, 42, 48, 46, 50, 44, 40, 38, 26, 22, 35, 52},
            {50, 40, 22, 28, 38, 44, 42, 46, 40, 36, 32, 20, 18, 30, 48},
            {52, 42, 25, 30, 40, 46, 44, 48, 42, 38, 34, 24, 20, 33, 50},
            {54, 44, 27, 31, 41, 47, 45, 49, 43, 39, 37, 25, 21, 34, 51},
            {48, 36, 18, 24, 34, 40, 38, 42, 36, 32, 28, 16, 14, 26, 44},
            {53, 43, 26, 31, 41, 47, 45, 49, 43, 39, 35, 25, 21, 34, 51},
            {51, 41, 24, 29, 39, 45, 43, 47, 41, 37, 33, 22, 19, 32, 49},
            {54, 44, 27, 31, 41, 47, 45, 49, 43, 39, 36, 25, 21, 34, 51}
        };

        int idx = Math.max(0, Math.min(intersectionId - 1, 7));
        for (int i = 0; i < times.length; i++) {
            String cong = speeds[idx][i] >= 40 ? "SMOOTH" : speeds[idx][i] >= 25 ? "SLOW" : "CONGESTED";
            list.add(new TrafficFlowDTO(intersectionId, times[i], data[idx][i], speeds[idx][i], cong));
        }
        return list;
    }

    @GetMapping("/intersections")
    public ResponseEntity<?> getIntersections() {
        return ResponseEntity.ok(getDummyIntersections());
    }

    @GetMapping("/intersections/{id}")
    public ResponseEntity<?> getIntersection(@PathVariable int id) {
        return getDummyIntersections().stream()
                .filter(i -> i.getId() == id)
                .findFirst()
                .map(i -> ResponseEntity.ok((Object) i))
                .orElse(ResponseEntity.status(404).body(Map.of("message", "교차로를 찾을 수 없습니다.")));
    }

    @GetMapping("/flow/{intersectionId}")
    public ResponseEntity<?> getTrafficFlow(@PathVariable int intersectionId) {
        return ResponseEntity.ok(getDummyTrafficFlow(intersectionId));
    }

    @GetMapping("/summary")
    public ResponseEntity<?> getSummary() {
        List<IntersectionDTO> all = getDummyIntersections();
        long total = all.size();
        long normalCount = all.stream().filter(i -> "NORMAL".equals(i.getStatus())).count();
        long cautionCount = all.stream().filter(i -> "CAUTION".equals(i.getStatus())).count();
        long emergencyCount = all.stream().filter(i -> "EMERGENCY".equals(i.getStatus())).count();
        long congestedCount = all.stream().filter(i -> "CONGESTED".equals(i.getCongestion())).count();

        Map<String, Object> summary = new LinkedHashMap<>();
        summary.put("totalIntersections", total);
        summary.put("normalCount", normalCount);
        summary.put("cautionCount", cautionCount);
        summary.put("emergencyCount", emergencyCount);
        summary.put("congestedCount", congestedCount);
        summary.put("avgCycleTime", 80);
        return ResponseEntity.ok(summary);
    }

    @PostMapping("/intersections/{id}/signal")
    public ResponseEntity<?> updateSignal(@PathVariable int id, @RequestBody Map<String, Integer> request) {
        Integer greenTime = request.get("greenTime");
        Integer yellowTime = request.get("yellowTime");
        Integer redTime = request.get("redTime");

        if (greenTime == null || yellowTime == null || redTime == null) {
            return ResponseEntity.badRequest().body(Map.of("message", "신호 시간을 모두 입력하세요."));
        }
        if (greenTime < 10 || greenTime > 120) {
            return ResponseEntity.badRequest().body(Map.of("message", "녹색 신호는 10~120초 범위여야 합니다."));
        }
        if (redTime < 10 || redTime > 120) {
            return ResponseEntity.badRequest().body(Map.of("message", "적색 신호는 10~120초 범위여야 합니다."));
        }

        // 더미: 실제로는 DB 업데이트
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("message", "신호 설정이 변경되었습니다.");
        result.put("intersectionId", id);
        result.put("greenTime", greenTime);
        result.put("yellowTime", yellowTime);
        result.put("redTime", redTime);
        result.put("totalCycle", greenTime + yellowTime + redTime);
        return ResponseEntity.ok(result);
    }
}
