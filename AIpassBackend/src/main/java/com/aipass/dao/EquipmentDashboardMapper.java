package com.aipass.dao;

import com.aipass.dto.EquipmentDashboardDTO;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

@Mapper
public interface EquipmentDashboardMapper {

    /** 전체 장비 목록 (최신 센서값 + 최근 정비일 JOIN). */
    List<EquipmentDashboardDTO> selectAll();

    /** 단건 조회. */
    EquipmentDashboardDTO selectById(@Param("equipmentId") Long equipmentId);
}
