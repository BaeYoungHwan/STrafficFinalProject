package com.aipass.dao;

import com.aipass.dto.ItsCollectLogDTO;
import org.apache.ibatis.annotations.Mapper;

import java.util.List;

@Mapper
public interface ItsCollectLogMapper {
    void insert(ItsCollectLogDTO dto);
    List<ItsCollectLogDTO> findRecent(int limit);
}
