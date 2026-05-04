package com.aipass.service;

import com.aipass.dao.EquipmentMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.time.temporal.ChronoUnit;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

@Service
public class EquipmentStateMachineService {

    private static final Logger logger = LoggerFactory.getLogger(EquipmentStateMachineService.class);
    private static final long T_MINUTE_SECONDS = 300;
    private static final long COOLDOWN_SECONDS = 600;

    private final EquipmentMapper equipmentMapper;
    private final ConcurrentHashMap<Long, LocalDateTime> anomalyStartMap = new ConcurrentHashMap<>();
    private final Set<Long> criticalLogged = ConcurrentHashMap.newKeySet();
    private final ConcurrentHashMap<Long, LocalDateTime> cooldownMap = new ConcurrentHashMap<>();

    public EquipmentStateMachineService(EquipmentMapper equipmentMapper) {
        this.equipmentMapper = equipmentMapper;
    }

    public String process(Long equipmentId, boolean isAnomaly, String riskLevel, String faultType) {
        LocalDateTime cooldownUntil = cooldownMap.get(equipmentId);
        if (cooldownUntil != null) {
            if (LocalDateTime.now().isBefore(cooldownUntil)) {
                equipmentMapper.updateRiskAndFault(equipmentId, "LOW", "NORMAL");
                return "LOW";
            }
            cooldownMap.remove(equipmentId);
            logger.info("[StateMachine] 장비 {} 쿨다운 만료 — 감시 재개", equipmentId);
        }

        if (isAnomaly) {
            LocalDateTime now = LocalDateTime.now();
            LocalDateTime start = anomalyStartMap.putIfAbsent(equipmentId, now);
            if (start == null) start = now;

            long elapsed = ChronoUnit.SECONDS.between(start, LocalDateTime.now());
            if (elapsed >= T_MINUTE_SECONDS) {
                riskLevel = "CRITICAL";
                if (criticalLogged.add(equipmentId)) {
                    logger.warn("[StateMachine] 장비 {} CRITICAL 진입 ({}초 연속 이상)", equipmentId, elapsed);
                }
            }
        } else {
            anomalyStartMap.remove(equipmentId);
            criticalLogged.remove(equipmentId);
        }

        equipmentMapper.updateRiskAndFault(equipmentId, riskLevel, faultType);
        return riskLevel;
    }

    public void clearCounter(Long equipmentId) {
        anomalyStartMap.remove(equipmentId);
        criticalLogged.remove(equipmentId);
        cooldownMap.put(equipmentId, LocalDateTime.now().plusSeconds(COOLDOWN_SECONDS));
        logger.info("[StateMachine] 장비 {} 수동 해제 — {}초 쿨다운 시작", equipmentId, COOLDOWN_SECONDS);
    }
}
