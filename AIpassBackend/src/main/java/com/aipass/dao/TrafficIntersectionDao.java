package com.aipass.dao;

import java.util.List;

import org.apache.ibatis.annotations.Mapper;
import org.springframework.stereotype.Repository;

import com.aipass.dto.TrafficIntersectionDetailDto;
import com.aipass.dto.TrafficIntersectionEquipmentDto;
import com.aipass.dto.TrafficIntersectionMaintenanceDto;
import com.aipass.dto.TrafficIntersectionSignalLogDto;

@Mapper
@Repository
public interface TrafficIntersectionDao {

    TrafficIntersectionDetailDto getIntersectionBaseInfo(Long intersectionId);

    List<TrafficIntersectionEquipmentDto> getIntersectionEquipmentList(Long intersectionId);

    List<TrafficIntersectionSignalLogDto> getIntersectionSignalLogList(Long intersectionId);

    List<TrafficIntersectionMaintenanceDto> getIntersectionMaintenanceList(Long intersectionId);
}