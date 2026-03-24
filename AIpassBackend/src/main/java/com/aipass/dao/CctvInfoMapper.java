package com.aipass.dao;

import com.aipass.dto.CctvInfoDTO;
import org.apache.ibatis.annotations.Mapper;

import java.util.List;

@Mapper
public interface CctvInfoMapper {
    void upsert(CctvInfoDTO dto);
    List<CctvInfoDTO> findAll();
}
