package com.aipass.service;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import com.aipass.dao.ViolationRecordDao;
import com.aipass.dto.ViolationRecordDto;

@Service
public class ViolationService {

    @Autowired
    private ViolationRecordDao violationRecordDao;

    public Map<String, Object> findPage(
            int page,
            int size,
            String plateNumber,
            String violationType,
            String fineStatus,
            String intersectionName
    ) {
        int offset = (page - 1) * size;

        Map<String, Object> paramMap = new HashMap<>();
        paramMap.put("offset", offset);
        paramMap.put("size", size);
        paramMap.put("plateNumber", plateNumber);
        paramMap.put("violationType", violationType);
        paramMap.put("fineStatus", fineStatus);
        paramMap.put("intersectionName", intersectionName);

        List<ViolationRecordDto> list = violationRecordDao.findPage(paramMap);
        int total = violationRecordDao.count(paramMap);

        Map<String, Object> result = new HashMap<>();
        result.put("data", list);
        result.put("total", total);
        result.put("page", page);
        result.put("size", size);

        return result;
    }

    public ViolationRecordDto findById(Long violationId) {
        return violationRecordDao.findById(violationId);
    }

    public boolean approve(Long violationId) {
        return violationRecordDao.approve(violationId) > 0;
    }

    public boolean reject(Long violationId) {
        return violationRecordDao.reject(violationId) > 0;
    }

    public boolean markCorrected(Long violationId) {
        return violationRecordDao.markCorrected(violationId) > 0;
    }
}