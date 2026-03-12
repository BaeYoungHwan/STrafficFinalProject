package com.aipass.controller;

import java.util.List;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import com.aipass.dto.TrafficMapPointDto;
import com.aipass.service.TrafficMapService;

@RestController
@CrossOrigin(origins = "*")
public class TrafficMapController {

    @Autowired
    private TrafficMapService trafficMapService;

    @GetMapping("/traffic/map-data")
    public List<TrafficMapPointDto> getTrafficMapData() {
        return trafficMapService.getTrafficMapData();
    }
}