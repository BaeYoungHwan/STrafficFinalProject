package com.aipass.controller;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.aipass.dto.SignalControlRequestDto;
import com.aipass.service.TrafficControlService;

@RestController
@RequestMapping("/traffic")
@CrossOrigin(origins = "*")
public class TrafficControlController {

    @Autowired
    private TrafficControlService trafficControlService;

    @PostMapping("/control")
    public boolean controlSignal(@RequestBody SignalControlRequestDto requestDto) {
        return trafficControlService.controlSignal(requestDto);
    }
}