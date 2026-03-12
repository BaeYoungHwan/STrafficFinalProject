package com.aipass.service;

import java.util.List;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import com.aipass.dao.TrafficIntersectionDao;
import com.aipass.dto.TrafficIntersectionDetailDto;
import com.aipass.dto.TrafficIntersectionEquipmentDto;
import com.aipass.dto.TrafficIntersectionMaintenanceDto;
import com.aipass.dto.TrafficIntersectionSignalLogDto;

@Service
public class TrafficIntersectionService {

    @Autowired
    private TrafficIntersectionDao trafficIntersectionDao;

    public TrafficIntersectionDetailDto getIntersectionDetail(Long intersectionId) {
        TrafficIntersectionDetailDto detail = trafficIntersectionDao.getIntersectionBaseInfo(intersectionId);

        if (detail == null) {
            return null;
        }

        List<TrafficIntersectionEquipmentDto> equipmentList =
                trafficIntersectionDao.getIntersectionEquipmentList(intersectionId);

        List<TrafficIntersectionSignalLogDto> signalLogList =
                trafficIntersectionDao.getIntersectionSignalLogList(intersectionId);

        List<TrafficIntersectionMaintenanceDto> maintenanceList =
                trafficIntersectionDao.getIntersectionMaintenanceList(intersectionId);

        detail.setEquipmentList(equipmentList);
        detail.setSignalLogList(signalLogList);
        detail.setMaintenanceList(maintenanceList);

        return detail;
    }
}