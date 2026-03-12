package com.aipass.dao;

import java.util.List;
import org.apache.ibatis.annotations.Mapper;
import org.springframework.stereotype.Repository;
import com.aipass.dto.DashboardDto;

@Mapper
@Repository
public interface DashboardDao {
    DashboardDto getDashboardSummary();
    List<Integer> getTrafficTrend();
    List<String> getRecentAlerts();
}