package com.aipass.service;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import com.aipass.dao.TrafficMapDao;
import com.aipass.dto.TrafficMapEquipmentDto;
import com.aipass.dto.TrafficMapFlatDto;
import com.aipass.dto.TrafficMapPointDto;

@Service
public class TrafficMapService {

    @Autowired
    private TrafficMapDao trafficMapDao;

    public List<TrafficMapPointDto> getTrafficMapData() {
        List<TrafficMapFlatDto> flatList = trafficMapDao.getTrafficMapData();

        Map<Long, TrafficMapPointDto> groupedMap = new LinkedHashMap<>();

        for (TrafficMapFlatDto row : flatList) {
            TrafficMapPointDto point = groupedMap.get(row.getIntersectionId());

            if (point == null) {
                point = new TrafficMapPointDto();
                point.setIntersectionId(row.getIntersectionId());
                point.setIntersectionName(row.getIntersectionName());
                point.setLatitude(row.getLatitude());
                point.setLongitude(row.getLongitude());
                point.setEquipmentList(new ArrayList<>());
                groupedMap.put(row.getIntersectionId(), point);
            }

            if (row.getEquipmentId() != null) {
                TrafficMapEquipmentDto equipment = new TrafficMapEquipmentDto();
                equipment.setEquipmentId(row.getEquipmentId());
                equipment.setEquipmentType(row.getEquipmentType());
                equipment.setStatus(row.getStatus());
                point.getEquipmentList().add(equipment);
            }
        }

        return new ArrayList<>(groupedMap.values());
    }
}