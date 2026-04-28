package com.aipass.controller;

import com.aipass.dao.EquipmentMapper;
import com.aipass.dao.SensorLogMapper;
import com.aipass.dto.EquipmentDashboardDTO;
import com.aipass.dto.SensorIngestRequest;
import com.aipass.service.EquipmentDashboardService;
import com.aipass.service.EquipmentStateMachineService;
import com.aipass.service.PredictiveMlClient;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.*;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/predictive")
public class PredictiveController {

    private static final Logger logger = LoggerFactory.getLogger(PredictiveController.class);

    private final EquipmentDashboardService dashboardService;
    private final EquipmentMapper equipmentMapper;
    private final EquipmentStateMachineService stateMachine;
    private final SensorLogMapper sensorLogMapper;
    private final PredictiveMlClient mlClient;
    private final JdbcTemplate jdbcTemplate;

    public PredictiveController(EquipmentDashboardService dashboardService,
                                EquipmentMapper equipmentMapper,
                                EquipmentStateMachineService stateMachine,
                                SensorLogMapper sensorLogMapper,
                                PredictiveMlClient mlClient,
                                JdbcTemplate jdbcTemplate) {
        this.dashboardService = dashboardService;
        this.equipmentMapper = equipmentMapper;
        this.stateMachine = stateMachine;
        this.sensorLogMapper = sensorLogMapper;
        this.mlClient = mlClient;
        this.jdbcTemplate = jdbcTemplate;
    }

    /**
     * GET /api/predictive/equipments
     * 전체 장비 목록 (필터/페이지네이션은 프론트에서 처리).
     */
    @GetMapping("/equipments")
    public ResponseEntity<Map<String, Object>> getEquipments() {
        Map<String, Object> result = new LinkedHashMap<>();
        try {
            List<EquipmentDashboardDTO> list = dashboardService.findAll();
            result.put("success", true);
            result.put("data", list);
            result.put("message", "장비 목록 조회 성공");
            return ResponseEntity.ok(result);
        } catch (Exception e) {
            logger.error("[PredictiveController.getEquipments] failed: {}", e.getMessage(), e);
            result.put("success", false);
            result.put("message", "장비 목록 조회 중 오류가 발생했습니다.");
            return ResponseEntity.status(500).body(result);
        }
    }

    /**
     * GET /api/predictive/equipments/{equipmentId}
     * 단건 조회 (상세 패널용).
     */
    @GetMapping("/equipments/{equipmentId}")
    public ResponseEntity<Map<String, Object>> getEquipmentDetail(
            @PathVariable("equipmentId") Long equipmentId
    ) {
        Map<String, Object> result = new LinkedHashMap<>();
        try {
            EquipmentDashboardDTO dto = dashboardService.findById(equipmentId);
            if (dto == null) {
                result.put("success", false);
                result.put("message", "해당 장비를 찾을 수 없습니다. equipmentId=" + equipmentId);
                return ResponseEntity.status(404).body(result);
            }
            result.put("success", true);
            result.put("data", dto);
            result.put("message", "장비 상세 조회 성공");
            return ResponseEntity.ok(result);
        } catch (Exception e) {
            logger.error("[PredictiveController.getEquipmentDetail] equipmentId={} failed: {}",
                    equipmentId, e.getMessage(), e);
            result.put("success", false);
            result.put("message", "장비 상세 조회 중 오류가 발생했습니다.");
            return ResponseEntity.status(500).body(result);
        }
    }

    /**
     * POST /api/predictive/predict
     * FE → BE → FastAPI ML 판정 프록시.
     * FE는 camelCase로 전송, BE가 FastAPI snake_case로 변환.
     */
    @PostMapping("/predict")
    public ResponseEntity<Map<String, Object>> predict(@RequestBody SensorIngestRequest request) {
        Map<String, Object> result = new LinkedHashMap<>();
        try {
            if (request == null || request.getItems() == null || request.getItems().isEmpty()) {
                result.put("success", false);
                result.put("message", "items가 비어있습니다.");
                return ResponseEntity.badRequest().body(result);
            }
            var predictions = mlClient.predict(request.getItems());
            result.put("success", true);
            result.put("data", predictions.values());
            result.put("message", "ML 판정 성공");
            return ResponseEntity.ok(result);
        } catch (Exception e) {
            logger.error("[PredictiveController.predict] failed: {}", e.getMessage(), e);
            result.put("success", false);
            result.put("message", "ML 판정 중 오류: " + e.getMessage());
            return ResponseEntity.status(500).body(result);
        }
    }

    /**
     * GET /api/predictive/equipments/{equipmentId}/sensor-history
     * 센서 이력 조회 (기간별 평균 다운샘플링).
     */
    @GetMapping("/equipments/{equipmentId}/sensor-history")
    public ResponseEntity<Map<String, Object>> getSensorHistory(
            @PathVariable("equipmentId") Long equipmentId,
            @RequestParam(value = "hours", defaultValue = "12") int hours
    ) {
        Map<String, Object> result = new LinkedHashMap<>();
        try {
            if (hours < 1) hours = 1;
            if (hours > 168) hours = 168;
            int interval = hours <= 12 ? 10 : hours <= 24 ? 20 : 60;
            List<Map<String, Object>> history = sensorLogMapper.selectHistory(equipmentId, hours, interval);
            result.put("success", true);
            result.put("data", history);
            result.put("message", "센서 이력 조회 성공");
            return ResponseEntity.ok(result);
        } catch (Exception e) {
            logger.error("[PredictiveController.getSensorHistory] equipmentId={} failed: {}",
                    equipmentId, e.getMessage(), e);
            result.put("success", false);
            result.put("message", "센서 이력 조회 중 오류가 발생했습니다.");
            return ResponseEntity.status(500).body(result);
        }
    }

    /**
     * GET /api/predictive/equipments/{equipmentId}/maintenance-history
     * 정비 기록 조회.
     */
    @GetMapping("/equipments/{equipmentId}/maintenance-history")
    public ResponseEntity<Map<String, Object>> getMaintenanceHistory(
            @PathVariable("equipmentId") Long equipmentId
    ) {
        Map<String, Object> result = new LinkedHashMap<>();
        try {
            List<Map<String, Object>> history = jdbcTemplate.queryForList(
                    "SELECT ticket_id, repair_status, reported_by, " +
                    "TO_CHAR(created_at, 'YYYY.MM.DD HH24:MI') AS created_at, " +
                    "TO_CHAR(resolved_at, 'YYYY.MM.DD HH24:MI') AS resolved_at " +
                    "FROM maintenance_log WHERE equipment_id = ? " +
                    "ORDER BY created_at DESC LIMIT 20",
                    equipmentId
            );
            result.put("success", true);
            result.put("data", history);
            result.put("message", "정비 기록 조회 성공");
            return ResponseEntity.ok(result);
        } catch (Exception e) {
            logger.error("[PredictiveController.getMaintenanceHistory] equipmentId={} failed: {}",
                    equipmentId, e.getMessage(), e);
            result.put("success", false);
            result.put("message", "정비 기록 조회 중 오류가 발생했습니다.");
            return ResponseEntity.status(500).body(result);
        }
    }

    /**
     * POST /api/predictive/equipments/{equipmentId}/resolve
     * CRITICAL 락 수동 해제 (관리자 조치 완료).
     */
    @PostMapping("/equipments/{equipmentId}/resolve")
    public ResponseEntity<Map<String, Object>> resolveEquipment(
            @PathVariable("equipmentId") Long equipmentId
    ) {
        Map<String, Object> result = new LinkedHashMap<>();
        try {
            stateMachine.clearCounter(equipmentId);
            int affected = equipmentMapper.resolveEquipment(equipmentId);
            if (affected == 0) {
                result.put("success", false);
                result.put("message", "해제 대상이 없습니다. (락 상태가 아니거나 존재하지 않는 장비)");
                return ResponseEntity.status(404).body(result);
            }

            boolean simulatorReset = mlClient.resetEquipment(equipmentId);

            logger.info("[PredictiveController] 장비 {} 수동 해제 완료 (시뮬레이터 리셋={})", equipmentId, simulatorReset);
            result.put("success", true);
            String message = "장비 상태가 정상으로 복원되었습니다.";
            if (!simulatorReset) {
                message += " (시뮬레이터 리셋 실패 — 시뮬레이터가 비활성화 상태일 수 있음)";
            }
            result.put("message", message);
            return ResponseEntity.ok(result);
        } catch (Exception e) {
            logger.error("[PredictiveController.resolveEquipment] equipmentId={} failed: {}",
                    equipmentId, e.getMessage(), e);
            result.put("success", false);
            result.put("message", "장비 해제 중 오류가 발생했습니다.");
            return ResponseEntity.status(500).body(result);
        }
    }
}
