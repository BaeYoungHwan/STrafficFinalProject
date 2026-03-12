package com.aipass.service;

import java.util.List;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.aipass.dao.DashboardDao;
import com.aipass.dto.DashboardDto;

@Service
@Transactional
public class DashboardService {

    @Autowired
    private DashboardDao dao;

    public DashboardDto getDashboardSummary() {
        DashboardDto dto = dao.getDashboardSummary();

        if (dto == null) {
            dto = new DashboardDto();
        }

        // 새로운 필드들 채우기
        List<Integer> trafficTrend = dao.getTrafficTrend();
        List<String> recentAlerts = dao.getRecentAlerts();

        dto.setTrafficTrend(trafficTrend);
        dto.setRecentAlerts(recentAlerts);

        return dto;
    }
}