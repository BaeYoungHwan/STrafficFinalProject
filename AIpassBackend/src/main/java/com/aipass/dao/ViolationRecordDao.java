package com.aipass.dao;

import java.util.List;
import java.util.Map;

import org.apache.ibatis.annotations.Mapper;
import org.springframework.stereotype.Repository;

import com.aipass.dto.ViolationRecordDto;

@Mapper
@Repository
public interface ViolationRecordDao {

    List<ViolationRecordDto> findPage(Map<String, Object> paramMap);

    int count(Map<String, Object> paramMap);

    ViolationRecordDto findById(Long violationId);

    int approve(Long violationId);

    int reject(Long violationId);

    int markCorrected(Long violationId);
}