package com.aipass.controller;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.*;
import java.util.stream.Collectors;
import java.util.Objects;

@RestController
@RequestMapping("/api/predictive")
public class PredictiveController {

    private static final Logger logger = LoggerFactory.getLogger(PredictiveController.class);

    // ───────────────────────────────────────────────────────────────────
    // 더미 데이터 (하드코딩)
    // ───────────────────────────────────────────────────────────────────
    private static final List<Map<String, Object>> DUMMY_EQUIPMENTS = new ArrayList<>();

    static {
        Object[][] raw = {
            // equipmentId, equipmentName, intersectionName, motorCurrent, bearingVibration, temperature, healthIndex, rul, riskLevel, status, lastInspectionDate, installationDate, isAnomaly, anomalyScore
            {1,  "CAM01", "강화대교",          15.2, 0.45, 42.5, 0.92, 365, "LOW",      "정상가동", "2026-03-15", "2023-01-10", false, 0.05},
            {2,  "CAM02", "용정리",            15.5, 0.50, 43.0, 0.88, 320, "LOW",      "정상가동", "2026-03-10", "2023-02-15", false, 0.08},
            {3,  "CAM03", "옥림교차로",        16.1, 0.65, 44.2, 0.78, 250, "LOW",      "정상가동", "2026-03-08", "2023-01-20", false, 0.12},
            {4,  "CAM04", "대산교차로",        17.8, 1.10, 48.5, 0.55, 120, "MEDIUM",   "정상가동", "2026-02-20", "2022-11-05", false, 0.38},
            {5,  "CAM05", "신당교차로",        18.5, 1.30, 50.0, 0.48,  85, "MEDIUM",   "정상가동", "2026-02-15", "2022-10-12", false, 0.45},
            {6,  "CAM06", "하도교",            16.0, 0.60, 43.8, 0.82, 280, "LOW",      "정상가동", "2026-03-12", "2023-03-01", false, 0.10},
            {7,  "CAM07", "부근교차로",        19.5, 1.80, 52.0, 0.35,  45, "HIGH",     "정상가동", "2026-01-25", "2022-08-20", true,  0.68},
            {8,  "CAM08", "하점교차로",        22.3, 1.80, 58.5, 0.28,  25, "HIGH",     "점검중",   "2026-03-20", "2022-06-15", true,  0.75},
            {9,  "CAM09", "이강교차로",        16.5, 0.70, 45.0, 0.75, 220, "LOW",      "정상가동", "2026-03-05", "2023-01-30", false, 0.15},
            {10, "CAM10", "소방심신휴센터",    45.1, 8.20, 88.0, 0.08,   2, "CRITICAL", "점검요망", "2026-03-25", "2021-12-10", true,  0.95},
            {11, "CAM11", "송산삼거리",        null, null, null, null, null, null,       "통신오류", "2026-02-28", "2022-09-05", false, null},
            {12, "CAM12", "인화삼거리",        15.8, 0.55, 43.5, 0.85, 300, "LOW",      "정상가동", "2026-03-01", "2023-02-28", false, 0.07},
        };

        for (Object[] r : raw) {
            Map<String, Object> eq = new LinkedHashMap<>();
            eq.put("equipmentId",       r[0]);
            eq.put("equipmentName",     r[1]);
            eq.put("intersectionName",  r[2]);
            eq.put("motorCurrent",      r[3]);
            eq.put("bearingVibration",  r[4]);
            eq.put("temperature",       r[5]);
            eq.put("healthIndex",       r[6]);
            eq.put("rul",               r[7]);
            eq.put("riskLevel",         r[8]);
            eq.put("status",            r[9]);
            eq.put("lastInspectionDate",r[10]);
            eq.put("installationDate",  r[11]);
            eq.put("isAnomaly",         r[12]);
            eq.put("anomalyScore",      r[13]);
            DUMMY_EQUIPMENTS.add(eq);
        }
    }

    // ───────────────────────────────────────────────────────────────────
    // API 1: 장비 목록 조회 (필터 + 페이지네이션)
    // GET /api/predictive/equipments
    // ───────────────────────────────────────────────────────────────────
    @GetMapping("/equipments")
    public ResponseEntity<Map<String, Object>> getEquipments(
            @RequestParam(value = "equipment", required = false) String equipment,
            @RequestParam(value = "riskLevel",  required = false) String riskLevel,
            @RequestParam(value = "status",     required = false) String status,
            @RequestParam(value = "page",       defaultValue = "1")  int page,
            @RequestParam(value = "size",       defaultValue = "20") int size
    ) {
        try {
            // 목록 응답용 필드만 추출 (상세 전용 필드 제외)
            List<Map<String, Object>> listFields = DUMMY_EQUIPMENTS.stream()
                    .map(eq -> {
                        Map<String, Object> item = new LinkedHashMap<>();
                        item.put("equipmentId",       eq.get("equipmentId"));
                        item.put("equipmentName",     eq.get("equipmentName"));
                        item.put("intersectionName",  eq.get("intersectionName"));
                        item.put("motorCurrent",      eq.get("motorCurrent"));
                        item.put("bearingVibration",  eq.get("bearingVibration"));
                        item.put("temperature",       eq.get("temperature"));
                        item.put("healthIndex",       eq.get("healthIndex"));
                        item.put("rul",               eq.get("rul"));
                        item.put("riskLevel",         eq.get("riskLevel"));
                        item.put("status",            eq.get("status"));
                        item.put("lastInspectionDate",eq.get("lastInspectionDate"));
                        return item;
                    })
                    .collect(Collectors.toList());

            // 필터링
            List<Map<String, Object>> filtered = listFields.stream()
                    .filter(eq -> {
                        if (equipment != null && !equipment.isEmpty()) {
                            String name = String.valueOf(eq.get("equipmentName"));
                            if (!name.toLowerCase().contains(equipment.toLowerCase())) return false;
                        }
                        if (riskLevel != null && !riskLevel.isEmpty()) {
                            if (!Objects.equals(riskLevel, eq.get("riskLevel"))) return false;
                        }
                        if (status != null && !status.isEmpty()) {
                            if (!Objects.equals(status, eq.get("status"))) return false;
                        }
                        return true;
                    })
                    .collect(Collectors.toList());

            // 페이지네이션
            int totalElements = filtered.size();
            int totalPages    = (int) Math.ceil((double) totalElements / size);
            int fromIndex     = Math.min((page - 1) * size, totalElements);
            int toIndex       = Math.min(fromIndex + size, totalElements);
            List<Map<String, Object>> pagedList = filtered.subList(fromIndex, toIndex);

            Map<String, Object> pagination = new LinkedHashMap<>();
            pagination.put("totalElements", totalElements);
            pagination.put("totalPages",    totalPages);
            pagination.put("currentPage",   page);
            pagination.put("size",          size);

            Map<String, Object> data = new LinkedHashMap<>();
            data.put("equipments", pagedList);
            data.put("pagination", pagination);

            Map<String, Object> result = new LinkedHashMap<>();
            result.put("success", true);
            result.put("data",    data);
            result.put("message", "장비 목록 조회 성공");
            return ResponseEntity.ok(result);

        } catch (Exception e) {
            logger.error("[getEquipments] 장비 목록 조회 실패: {}", e.getMessage(), e);
            Map<String, Object> error = new LinkedHashMap<>();
            error.put("success", false);
            error.put("message", "장비 목록 조회 중 오류가 발생했습니다.");
            return ResponseEntity.status(500).body(error);
        }
    }

    // ───────────────────────────────────────────────────────────────────
    // API 2: 장비 상세 조회
    // GET /api/predictive/equipments/{equipmentId}
    // ───────────────────────────────────────────────────────────────────
    @GetMapping("/equipments/{equipmentId}")
    public ResponseEntity<Map<String, Object>> getEquipmentDetail(
            @PathVariable("equipmentId") int equipmentId
    ) {
        try {
            Optional<Map<String, Object>> found = DUMMY_EQUIPMENTS.stream()
                    .filter(eq -> equipmentId == (int) eq.get("equipmentId"))
                    .findFirst();

            if (found.isEmpty()) {
                Map<String, Object> notFound = new LinkedHashMap<>();
                notFound.put("success", false);
                notFound.put("message", "해당 장비를 찾을 수 없습니다. equipmentId=" + equipmentId);
                return ResponseEntity.status(404).body(notFound);
            }

            Map<String, Object> result = new LinkedHashMap<>();
            result.put("success", true);
            result.put("data",    found.get());
            result.put("message", "장비 상세 조회 성공");
            return ResponseEntity.ok(result);

        } catch (Exception e) {
            logger.error("[getEquipmentDetail] 장비 상세 조회 실패: equipmentId={}, {}", equipmentId, e.getMessage(), e);
            Map<String, Object> error = new LinkedHashMap<>();
            error.put("success", false);
            error.put("message", "장비 상세 조회 중 오류가 발생했습니다.");
            return ResponseEntity.status(500).body(error);
        }
    }
}
