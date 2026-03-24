package com.aipass.service;

import com.aipass.dao.ItsCollectLogMapper;
import com.aipass.dto.ItsCollectLogDTO;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class ItsCollectLogService {

    private final ItsCollectLogMapper collectLogMapper;

    public ItsCollectLogService(ItsCollectLogMapper collectLogMapper) {
        this.collectLogMapper = collectLogMapper;
    }

    public void logSuccess(String collectType, int totalCount, int newCount) {
        ItsCollectLogDTO dto = new ItsCollectLogDTO(collectType, "SUCCESS", totalCount, newCount);
        collectLogMapper.insert(dto);
    }

    public void logFail(String collectType, String errorMessage) {
        ItsCollectLogDTO dto = new ItsCollectLogDTO(collectType, "FAIL", 0, 0);
        dto.setErrorMessage(errorMessage);
        collectLogMapper.insert(dto);
    }

    public List<ItsCollectLogDTO> getRecentLogs(int limit) {
        return collectLogMapper.findRecent(limit);
    }
}
