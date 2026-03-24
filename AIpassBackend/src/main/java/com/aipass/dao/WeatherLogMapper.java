package com.aipass.dao;

import com.aipass.dto.WeatherLogDTO;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

@Mapper
public interface WeatherLogMapper {
    void insert(WeatherLogDTO dto);
    WeatherLogDTO findLatest(@Param("intersectionId") Long intersectionId);
}
