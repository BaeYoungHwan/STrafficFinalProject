package com.aipass.dao;

import com.aipass.dto.CctvDTO;
import org.apache.ibatis.annotations.Mapper;

import java.util.List;

@Mapper
public interface CctvMapper {
    List<CctvDTO> findAllActive();
    CctvDTO findById(String cctvId);
    CctvDTO findAiTargetCctv();
}
