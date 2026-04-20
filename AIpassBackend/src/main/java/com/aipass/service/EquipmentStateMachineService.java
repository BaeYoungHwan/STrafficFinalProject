package com.aipass.service;

import com.aipass.dao.EquipmentMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.time.temporal.ChronoUnit;
import java.util.concurrent.ConcurrentHashMap;

/**
 * 메모리 기반 상태머신.
 * 5분(300초) 연속 이상 감지 시 equipment.risk_level → CRITICAL.
 * 해제는 관리자 수동 (resolveEquipment).
 */
@Service
public class EquipmentStateMachineService {

    private static final Logger logger = LoggerFactory.getLogger(EquipmentStateMachineService.class);
    private static final long T_MINUTE_SECONDS = 300;

    private final EquipmentMapper equipmentMapper;
    private final ConcurrentHashMap<Long, LocalDateTime> anomalyStartMap = new ConcurrentHashMap<>();

    public EquipmentStateMachineService(EquipmentMapper equipmentMapper) {
        this.equipmentMapper = equipmentMapper;
    }

    /**
     * @return 최종 risk_level (영문)
     */
    public String process(Long equipmentId, boolean isAnomaly, String riskLevel, String faultType) {
        if (isAnomaly) {
            LocalDateTime start = anomalyStartMap.putIfAbsent(equipmentId, LocalDateTime.now());
            if (start == null) start = anomalyStartMap.get(equipmentId);

            long elapsed = ChronoUnit.SECONDS.between(start, LocalDateTime.now());
            if (elapsed >= T_MINUTE_SECONDS) {
                riskLevel = "CRITICAL";
                logger.warn("[StateMachine] 장비 {} CRITICAL ({}초 연속 이상)", equipmentId, elapsed);
            }
        } else {
            anomalyStartMap.remove(equipmentId);
        }

        equipmentMapper.updateRiskAndFault(equipmentId, riskLevel, faultType);
        return riskLevel;
    }

    public void clearCounter(Long equipmentId) {
        anomalyStartMap.remove(equipmentId);
    }
}
