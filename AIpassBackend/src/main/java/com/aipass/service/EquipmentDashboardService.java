package com.aipass.service;

import com.aipass.dao.EquipmentDashboardMapper;
import com.aipass.dto.EquipmentDashboardDTO;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class EquipmentDashboardService {

    private final EquipmentDashboardMapper mapper;

    public EquipmentDashboardService(EquipmentDashboardMapper mapper) {
        this.mapper = mapper;
    }

    public List<EquipmentDashboardDTO> findAll() {
        return mapper.selectAll();
    }

    public EquipmentDashboardDTO findById(Long equipmentId) {
        return mapper.selectById(equipmentId);
    }
}
