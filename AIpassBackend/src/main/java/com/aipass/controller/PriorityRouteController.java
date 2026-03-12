package com.aipass.controller;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import com.aipass.dto.PriorityRouteRequestDto;
import com.aipass.dto.PriorityRouteResponseDto;
import com.aipass.service.PriorityRouteService;

/*
 * [PriorityRouteController]
 *
 * 긴급 차량 우선 경로 계산 API
 *
 * POST /traffic/priority-route
 */

@RestController
@CrossOrigin(origins = "*")
public class PriorityRouteController {

    @Autowired
    private PriorityRouteService priorityRouteService;

    /*
     * 긴급 차량 경로 요청 API
     */
    @PostMapping("/traffic/priority-route")
    public PriorityRouteResponseDto getPriorityRoute(
            @RequestBody PriorityRouteRequestDto requestDto) {

        return priorityRouteService.getPriorityRoute(requestDto);
    }
}