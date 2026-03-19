package com.aipass.controller;

import com.aipass.dao.ViolationMapper;
import com.aipass.dto.ViolationDTO;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/enforcement")
public class EnforcementController {

    private final ViolationMapper violationMapper;

    public EnforcementController(ViolationMapper violationMapper) {
        this.violationMapper = violationMapper;
    }

    /**
     * FastAPI에서 과속 위반 이벤트를 수신 (세션 인증 제외 대상)
     */
    @PostMapping("/webhook")
    public ResponseEntity<?> receiveWebhook(@RequestBody Map<String, Object> body) {
        try {
            ViolationDTO dto = new ViolationDTO();
            dto.setEventId((String) body.get("eventId"));

            // mockLprData에서 번호판 정보 추출
            Object lprRaw = body.get("mockLprData");
            if (lprRaw instanceof Map) {
                @SuppressWarnings("unchecked")
                Map<String, Object> lpr = (Map<String, Object>) lprRaw;
                dto.setPlateNumber((String) lpr.getOrDefault("plateNumber", "미인식"));
                dto.setPlateImageBase64((String) lpr.get("plateImageBase64"));
            } else {
                dto.setPlateNumber("미인식");
            }

            // 위반 유형 변환
            String rawType = (String) body.getOrDefault("violationType", "기타");
            dto.setViolationType(translateViolationType(rawType));

            // 위치
            dto.setLocation((String) body.getOrDefault("cameraLocation", "강화대교_메인_01"));

            // 속도
            Object speed = body.get("speedKmh");
            if (speed instanceof Number) {
                dto.setSpeedKmh(((Number) speed).doubleValue());
            }

            violationMapper.insert(dto);
            return ResponseEntity.ok(Map.of("success", true));
        } catch (Exception e) {
            return ResponseEntity.status(500).body(Map.of("success", false, "message", e.getMessage()));
        }
    }

    /**
     * 단속 내역 목록 조회 (필터 + 페이지네이션)
     */
    @GetMapping("/violations")
    public ResponseEntity<?> getViolations(
            @RequestParam(required = false) String plateNumber,
            @RequestParam(required = false) String violationType,
            @RequestParam(required = false) String status,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size) {

        Map<String, Object> params = new HashMap<>();
        params.put("plateNumber", plateNumber);
        params.put("violationType", violationType);
        params.put("status", status);
        params.put("size", size);
        params.put("offset", (page - 1) * size);

        List<ViolationDTO> items = violationMapper.findAll(params);
        int total = violationMapper.countAll(params);

        Map<String, Object> data = new HashMap<>();
        data.put("items", items);
        data.put("total", total);
        data.put("page", page);
        data.put("size", size);
        data.put("totalPages", (int) Math.ceil((double) total / size));

        return ResponseEntity.ok(Map.of("success", true, "data", data));
    }

    /**
     * 단속 내역 상세 조회
     */
    @GetMapping("/violations/{id}")
    public ResponseEntity<?> getViolation(@PathVariable Long id) {
        ViolationDTO dto = violationMapper.findById(id);
        if (dto == null) {
            return ResponseEntity.status(404).body(Map.of("success", false, "message", "해당 단속 내역을 찾을 수 없습니다."));
        }
        return ResponseEntity.ok(Map.of("success", true, "data", dto));
    }

    /**
     * 단속 상태 변경 (승인 / 반려)
     */
    @PutMapping("/violations/{id}/status")
    public ResponseEntity<?> updateStatus(@PathVariable Long id, @RequestBody Map<String, String> body) {
        String newStatus = body.get("status");
        if (newStatus == null || (!newStatus.equals("승인") && !newStatus.equals("반려"))) {
            return ResponseEntity.badRequest().body(Map.of("success", false, "message", "유효하지 않은 상태값입니다. (승인 또는 반려)"));
        }
        ViolationDTO existing = violationMapper.findById(id);
        if (existing == null) {
            return ResponseEntity.status(404).body(Map.of("success", false, "message", "해당 단속 내역을 찾을 수 없습니다."));
        }
        violationMapper.updateStatus(id, newStatus);
        return ResponseEntity.ok(Map.of("success", true, "message", "상태가 변경되었습니다."));
    }

    private String translateViolationType(String raw) {
        if (raw == null) return "기타";
        switch (raw.toUpperCase()) {
            case "SPEEDING": return "과속";
            case "RED_LIGHT": return "신호위반";
            case "CENTER_LINE": return "중앙선 침범";
            case "LINE_CROSSING": return "차선 위반";
            default: return raw;
        }
    }
}
