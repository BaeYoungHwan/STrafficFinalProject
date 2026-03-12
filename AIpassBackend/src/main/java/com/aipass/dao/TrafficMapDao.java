package com.aipass.dao;

import java.util.List;

import org.apache.ibatis.annotations.Mapper;
import org.springframework.stereotype.Repository;

import com.aipass.dto.TrafficMapFlatDto;

@Mapper
@Repository
public interface TrafficMapDao {

    List<TrafficMapFlatDto> getTrafficMapData();
}