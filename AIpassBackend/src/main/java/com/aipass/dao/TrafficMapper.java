package com.aipass.dao;

import com.aipass.dto.TrafficFlowHourDTO;
import com.aipass.dto.TrafficIntersectionDTO;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;
import java.util.Map;

@Mapper
public interface TrafficMapper {

    List<TrafficIntersectionDTO> findAll();

    TrafficIntersectionDTO findById(@Param("id") Long id);

    void updateSignal(@Param("id") Long id,
                      @Param("green") int green,
                      @Param("yellow") int yellow,
                      @Param("red") int red);

    List<TrafficFlowHourDTO> findFlowByHour(@Param("limit") int limit);

    Map<String, Object> findSummary();
}
