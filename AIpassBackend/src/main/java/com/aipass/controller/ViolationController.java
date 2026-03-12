package com.aipass.controller;

import java.util.Map;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import com.aipass.dto.ViolationRecordDto;
import com.aipass.service.ViolationService;

@RestController
@RequestMapping("/violations")
@CrossOrigin(origins = "*")
public class ViolationController {

    @Autowired
    private ViolationService violationService;

    @GetMapping
    public Map<String, Object> findPage(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            @RequestParam(required = false) String plateNumber,
            @RequestParam(required = false) String violationType,
            @RequestParam(required = false) String fineStatus,
            @RequestParam(required = false) String intersectionName
    ) {
        return violationService.findPage(page, size, plateNumber, violationType, fineStatus, intersectionName);
    }

    @GetMapping("/{violationId}")
    public ViolationRecordDto findById(@PathVariable Long violationId) {
        return violationService.findById(violationId);
    }

    @PatchMapping("/{violationId}/approve")
    public boolean approve(@PathVariable Long violationId) {
        return violationService.approve(violationId);
    }

    @PatchMapping("/{violationId}/reject")
    public boolean reject(@PathVariable Long violationId) {
        return violationService.reject(violationId);
    }

    @PatchMapping("/{violationId}/correct")
    public boolean markCorrected(@PathVariable Long violationId) {
        return violationService.markCorrected(violationId);
    }
}