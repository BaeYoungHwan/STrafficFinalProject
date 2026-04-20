package com.aipass.dao;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

@Mapper
public interface EquipmentMapper {

    void updateRiskAndFault(
            @Param("equipmentId") Long equipmentId,
            @Param("riskLevel") String riskLevel,
            @Param("faultType") String faultType
    );

    int resolveEquipment(@Param("equipmentId") Long equipmentId);
}
