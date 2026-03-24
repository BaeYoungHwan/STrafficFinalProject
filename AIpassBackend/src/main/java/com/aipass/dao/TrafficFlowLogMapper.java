package com.aipass.dao;

import com.aipass.dto.TrafficFlowLogDTO;
import org.apache.ibatis.annotations.Mapper;

import java.util.List;

@Mapper
public interface TrafficFlowLogMapper {
    void insertBatch(List<TrafficFlowLogDTO> list);
    List<TrafficFlowLogDTO> findRecent(int limit);
}
