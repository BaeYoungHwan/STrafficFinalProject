package com.aipass.dao;

import com.aipass.dto.ItsRouteDTO;
import org.apache.ibatis.annotations.Mapper;

import java.util.List;

@Mapper
public interface ItsRouteMapper {
    List<ItsRouteDTO> findActiveRoutes();
}
