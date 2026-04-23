package com.aipass.dao;

import com.aipass.dto.SensorLogDTO;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;
import java.util.Map;

@Mapper
public interface SensorLogMapper {
    void insertBatch(@Param("items") List<SensorLogDTO> items);
    int countAll();

    List<Map<String, Object>> selectHistory(
            @Param("equipmentId") Long equipmentId,
            @Param("hours") int hours,
            @Param("interval") int interval
    );
}
