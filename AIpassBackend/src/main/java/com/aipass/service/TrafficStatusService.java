package com.aipass.service;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import com.aipass.dao.TrafficStatusDao;
import com.aipass.dto.TrafficStatusDto;

@Service
public class TrafficStatusService {

    @Autowired
    private TrafficStatusDao trafficStatusDao;

    public TrafficStatusDto getTrafficStatus() {
        TrafficStatusDto dto = trafficStatusDao.getTrafficStatus();

        if (dto == null) {
            dto = new TrafficStatusDto();
            dto.setTemperature(0.0);
            dto.setVibration(0.0);
            dto.setRiskScore(0.0);
            dto.setSignalPercent(0);
            dto.setSignalState("점검필요");
            dto.setCameraPercent(0);
            dto.setCameraState("점검필요");
            dto.setOperationStatus("점검필요");
            dto.setFailureRisk("높음");
            dto.setLastMaintenanceText("정보 없음");
        }

        return dto;
    }
}