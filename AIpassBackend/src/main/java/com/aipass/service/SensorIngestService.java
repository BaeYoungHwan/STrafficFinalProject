package com.aipass.service;

import com.aipass.dao.SensorLogMapper;
import com.aipass.dto.PredictResponse.PredictionItem;
import com.aipass.dto.SensorIngestItemDTO;
import com.aipass.dto.SensorLogDTO;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

@Service
public class SensorIngestService {

    private static final Logger logger = LoggerFactory.getLogger(SensorIngestService.class);

    private final EquipmentStateMachineService stateMachine;
    private final SensorLogMapper sensorLogMapper;

    public SensorIngestService(EquipmentStateMachineService stateMachine, SensorLogMapper sensorLogMapper) {
        this.stateMachine = stateMachine;
        this.sensorLogMapper = sensorLogMapper;
    }

    @Transactional
    public int ingestBatch(List<SensorIngestItemDTO> items, Map<Long, PredictionItem> predictions) {
        if (items == null || items.isEmpty()) return 0;

        List<SensorLogDTO> logRows = new ArrayList<>();

        for (SensorIngestItemDTO raw : items) {
            Long eqId = raw.getEquipmentId();
            PredictionItem pred = predictions.get(eqId);
            if (pred == null) {
                logger.warn("[SensorIngest] equipmentId={} 판정 결과 누락, skip", eqId);
                continue;
            }

            String riskLevel = pred.getRiskLevel() != null ? pred.getRiskLevel() : "LOW";

            String finalRisk = stateMachine.process(
                    eqId,
                    Boolean.TRUE.equals(pred.getIsAnomaly()),
                    riskLevel,
                    pred.getFaultType()
            );

            SensorLogDTO log = new SensorLogDTO();
            log.setEquipmentId(eqId);
            log.setVibration(raw.getVibration());
            log.setTemperature(raw.getTemperature());
            log.setMotorCurrent(raw.getMotorCurrent());
            log.setRecordedAt(raw.getRecordedAt());
            log.setIsAnomaly(pred.getIsAnomaly());
            log.setAnomalyScore(pred.getAnomalyScore());
            log.setFaultType(pred.getFaultType());
            log.setRiskLevel(finalRisk);
            logRows.add(log);
        }

        if (!logRows.isEmpty()) {
            sensorLogMapper.insertBatch(logRows);
        }

        logger.debug("[SensorIngest] saved={}", logRows.size());
        return logRows.size();
    }
}
