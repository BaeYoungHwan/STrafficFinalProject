package com.aipass.controller;

import com.aipass.dao.ViolationMapper;
import com.aipass.dto.ViolationDTO;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/enforcement")
public class EnforcementController {

    private static final Logger logger = LoggerFactory.getLogger(EnforcementController.class);

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
            dto.setIntersectionId(null); // FastAPI는 intersection_id 미제공

            // mockLprData에서 번호판 정보 추출
            Object lprRaw = body.get("mockLprData");
            if (lprRaw instanceof Map) {
                @SuppressWarnings("unchecked")
                Map<String, Object> lpr = (Map<String, Object>) lprRaw;
                dto.setPlateNumber((String) lpr.getOrDefault("plateNumber", "미인식"));
                // base64 이미지는 image_url에 저장하지 않음 (URL 타입이므로 null 처리)
                dto.setImageUrl(null);
            } else {
                dto.setPlateNumber("미인식");
            }

            dto.setViolationType(translateViolationType((String) body.get("violationType")));

            // 위치: cameraLocation을 image_url 대신 violation_type 뒤에 붙이거나 intersection 조회
            // 현재는 단순 저장 (intersection_id=null 허용)

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
     * status 파라미터: 대기중 / 승인 / 반려 → DB: UNPROCESSED / APPROVED / REJECTED 로 변환
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
        params.put("fineStatus", toDbStatus(status)); // 한국어 → DB 코드
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
     * 단속 상태 변경: 프론트 (승인/반려) → DB (APPROVED/REJECTED)
     */
    @PutMapping("/violations/{id}/status")
    public ResponseEntity<?> updateStatus(@PathVariable Long id, @RequestBody Map<String, String> body) {
        String korStatus = body.get("status");
        String dbStatus = toDbStatus(korStatus);

        if (dbStatus == null || dbStatus.equals("UNPROCESSED")) {
            return ResponseEntity.badRequest().body(Map.of("success", false, "message", "유효하지 않은 상태값입니다. (승인 또는 반려)"));
        }
        ViolationDTO existing = violationMapper.findById(id);
        if (existing == null) {
            return ResponseEntity.status(404).body(Map.of("success", false, "message", "해당 단속 내역을 찾을 수 없습니다."));
        }
        violationMapper.updateStatus(id, dbStatus);
        return ResponseEntity.ok(Map.of("success", true, "message", "상태가 변경되었습니다."));
    }

    /**
     * 단속 내역 수정: 차량번호, 위반유형, 상태 변경 + is_corrected=true
     */
    @PutMapping("/violations/{id}")
    public ResponseEntity<?> updateViolation(@PathVariable Long id, @RequestBody Map<String, String> body) {
        ViolationDTO existing = violationMapper.findById(id);
        if (existing == null) {
            return ResponseEntity.status(404).body(Map.of("success", false, "message", "해당 단속 내역을 찾을 수 없습니다."));
        }
        ViolationDTO dto = new ViolationDTO();
        dto.setViolationId(id);
        dto.setPlateNumber(body.getOrDefault("plateNumber", existing.getPlateNumber()));
        dto.setViolationType(body.getOrDefault("violationType", existing.getViolationType()));
        String korStatus = body.get("status");
        String dbStatus = toDbStatus(korStatus);
        dto.setFineStatus(dbStatus != null ? dbStatus : existing.getFineStatus());
        try {
            violationMapper.update(dto);
            return ResponseEntity.ok(Map.of("success", true, "message", "수정이 완료되었습니다."));
        } catch (Exception e) {
            logger.error("[updateViolation] DB 업데이트 실패 id={}: {}", id, e.getMessage(), e);
            return ResponseEntity.status(500).body(Map.of("success", false, "message", "수정 중 오류: " + e.getMessage()));
        }
    }

    // 위반유형 영문 → 한국어
    private String translateViolationType(String raw) {
        if (raw == null) return "기타";
        switch (raw.toUpperCase()) {
            case "SPEEDING":      return "과속";
            case "RED_LIGHT":     return "신호위반";
            case "CENTER_LINE":   return "중앙선 침범";
            case "LINE_CROSSING": return "차선 위반";
            default:              return raw;
        }
    }

    // 한국어 상태 → DB 코드
    private String toDbStatus(String kor) {
        if (kor == null || kor.isEmpty()) return null;
        switch (kor) {
            case "승인":   return "APPROVED";
            case "반려":   return "REJECTED";
            case "대기중": return "UNPROCESSED";
            default:       return null;
        }
    }
}
