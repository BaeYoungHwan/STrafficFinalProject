package com.aipass.controller;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import com.aipass.dto.TrafficStatusDto;
import com.aipass.service.TrafficStatusService;

@RestController
@CrossOrigin(origins = "*")
public class TrafficStatusController {

    @Autowired
    private TrafficStatusService trafficStatusService;

    @GetMapping("/traffic/status")
    public TrafficStatusDto getTrafficStatus() {
        return trafficStatusService.getTrafficStatus();
    }
}