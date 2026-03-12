package com.aipass.service;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import com.aipass.dao.TrafficControlDao;
import com.aipass.dto.SignalControlRequestDto;

@Service
public class TrafficControlService {

    @Autowired
    private TrafficControlDao trafficControlDao;

    public boolean controlSignal(SignalControlRequestDto requestDto) {
        if (requestDto == null) {
            return false;
        }

        if (requestDto.getIntersectionId() == null) {
            return false;
        }

        if (requestDto.getControlType() == null || requestDto.getControlType().trim().isEmpty()) {
            return false;
        }

        if (requestDto.getControlReason() == null || requestDto.getControlReason().trim().isEmpty()) {
            return false;
        }

        return trafficControlDao.insertSignalControlLog(requestDto) > 0;
    }
}