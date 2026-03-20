package com.aipass.dao;

import com.aipass.dto.ViolationDTO;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;
import java.util.Map;

@Mapper
public interface ViolationMapper {
    List<ViolationDTO> findAll(Map<String, Object> params);
    int countAll(Map<String, Object> params);
    ViolationDTO findById(Long id);
    void insert(ViolationDTO dto);
    void updateStatus(@Param("id") Long id, @Param("status") String status);
    void update(ViolationDTO dto);
}
