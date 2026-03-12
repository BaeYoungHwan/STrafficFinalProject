package com.aipass.dao;

import org.apache.ibatis.annotations.Mapper;
import org.springframework.stereotype.Repository;

import com.aipass.dto.TrafficStatusDto;

@Mapper
@Repository
public interface TrafficStatusDao {

    TrafficStatusDto getTrafficStatus();
}