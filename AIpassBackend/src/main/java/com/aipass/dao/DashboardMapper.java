package com.aipass.dao;

import com.aipass.dto.DashboardIntersectionDTO;
import com.aipass.dto.DashboardViolationSummaryDTO;
import com.aipass.dto.WeatherLogDTO;
import com.aipass.dto.RoadSegmentDTO;
import com.aipass.dto.DashboardTrafficSummaryDTO;
import com.aipass.dto.DashboardCctvStatusDTO;
import org.apache.ibatis.annotations.Mapper;

import java.util.List;

@Mapper
public interface DashboardMapper {
    List<DashboardIntersectionDTO> findAllIntersections();
    WeatherLogDTO findLatestWeather();
    DashboardViolationSummaryDTO findTodayViolationSummary();

    List<RoadSegmentDTO> findRoadSegments();
    List<RoadSegmentDTO> findRoadSegmentsByDirection(String direction);
    DashboardTrafficSummaryDTO findTrafficSummary();
    Long findTrafficCountByDate(String date);
    DashboardCctvStatusDTO findCctvStatus();
}
