package com.aipass.controller;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import com.aipass.dto.DashboardDto;
import com.aipass.service.DashboardService;

@RestController
public class DashboardController {

    @Autowired
    private DashboardService dashboardService;

    @GetMapping("/dashboard/summary")
    public DashboardDto getDashboardSummary() {
        return dashboardService.getDashboardSummary();
    }
}