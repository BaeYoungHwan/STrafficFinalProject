package com.aipass.controller;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;

import com.aipass.dto.TrafficIntersectionDetailDto;
import com.aipass.service.TrafficIntersectionService;

@RestController
@CrossOrigin(origins = "*")
public class TrafficIntersectionController {

    @Autowired
    private TrafficIntersectionService trafficIntersectionService;

    @GetMapping("/traffic/intersection/{intersectionId}")
    public TrafficIntersectionDetailDto getIntersectionDetail(@PathVariable Long intersectionId) {
        return trafficIntersectionService.getIntersectionDetail(intersectionId);
    }
}