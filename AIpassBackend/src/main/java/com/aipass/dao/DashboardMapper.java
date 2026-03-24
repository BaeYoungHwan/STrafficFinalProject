package com.aipass.dao;

import com.aipass.dto.DashboardIntersectionDTO;
import com.aipass.dto.DashboardViolationSummaryDTO;
import com.aipass.dto.WeatherLogDTO;
import org.apache.ibatis.annotations.Mapper;

import java.util.List;

@Mapper
public interface DashboardMapper {
    List<DashboardIntersectionDTO> findAllIntersections();
    WeatherLogDTO findLatestWeather();
    DashboardViolationSummaryDTO findTodayViolationSummary();
}
