package com.aipass.dao;

import java.util.List;

import org.apache.ibatis.annotations.Mapper;
import org.springframework.stereotype.Repository;

import com.aipass.dto.SignalControlRequestDto;
import com.aipass.dto.TrafficMapDto;

@Mapper
@Repository
public interface TrafficControlDao {

    List<TrafficMapDto> findTrafficMapData();

    int insertSignalControlLog(SignalControlRequestDto requestDto);
}