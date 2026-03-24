package com.aipass.scheduler;

import com.aipass.dao.ItsRouteMapper;
import com.aipass.dao.TrafficFlowLogMapper;
import com.aipass.dto.ItsRouteDTO;
import com.aipass.dto.TrafficFlowLogDTO;
import com.aipass.service.ItsCollectLogService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.math.BigDecimal;
import java.net.URI;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

@Component
public class TrafficFlowCollectScheduler {

    private static final Logger log = LoggerFactory.getLogger(TrafficFlowCollectScheduler.class);
    private static final DateTimeFormatter ITS_DATE_FORMAT = DateTimeFormatter.ofPattern("yyyyMMddHHmmss");

    private final RestTemplate restTemplate;
    private final ItsRouteMapper itsRouteMapper;
    private final TrafficFlowLogMapper trafficFlowLogMapper;
    private final ItsCollectLogService collectLogService;

    @Value("${its.api.key}")
    private String apiKey;

    @Value("${its.api.base-url}")
    private String baseUrl;

    public TrafficFlowCollectScheduler(RestTemplate restTemplate,
                                       ItsRouteMapper itsRouteMapper,
                                       TrafficFlowLogMapper trafficFlowLogMapper,
                                       ItsCollectLogService collectLogService) {
        this.restTemplate = restTemplate;
        this.itsRouteMapper = itsRouteMapper;
        this.trafficFlowLogMapper = trafficFlowLogMapper;
        this.collectLogService = collectLogService;
    }

    @Scheduled(cron = "0 */5 * * * *")
    public void collect() {
        log.info("[TRAFFIC_FLOW] 수집 시작");
        try {
            List<ItsRouteDTO> routes = itsRouteMapper.findActiveRoutes();
            if (routes == null || routes.isEmpty()) {
                log.info("[TRAFFIC_FLOW] 활성 노선 없음 — 수집 스킵");
                return;
            }

            List<TrafficFlowLogDTO> allData = new ArrayList<>();

            for (ItsRouteDTO route : routes) {
                if (Boolean.TRUE.equals(route.getCollectUp())) {
                    List<TrafficFlowLogDTO> upData = fetchByDirection(route.getRouteNo(), "start", "UP");
                    allData.addAll(upData);
                }
                if (Boolean.TRUE.equals(route.getCollectDown())) {
                    List<TrafficFlowLogDTO> downData = fetchByDirection(route.getRouteNo(), "end", "DOWN");
                    allData.addAll(downData);
                }
            }

            if (!allData.isEmpty()) {
                trafficFlowLogMapper.insertBatch(allData);
            }

            collectLogService.logSuccess("TRAFFIC_FLOW", allData.size(), allData.size());
            log.info("[TRAFFIC_FLOW] 수집 완료 — {}개 노선, {}건 저장", routes.size(), allData.size());

        } catch (Exception e) {
            collectLogService.logFail("TRAFFIC_FLOW", e.getMessage());
            log.error("[TRAFFIC_FLOW] 수집 실패", e);
        }
    }

    private List<TrafficFlowLogDTO> fetchByDirection(String routeNo, String drcType, String direction) {
        List<TrafficFlowLogDTO> result = new ArrayList<>();
        try {
            String url = baseUrl + "/trafficInfo"
                    + "?apiKey=" + apiKey
                    + "&type=its"
                    + "&routeNo=" + routeNo
                    + "&drcType=" + drcType
                    + "&minX=126.350"
                    + "&maxX=126.550"
                    + "&minY=37.720"
                    + "&maxY=37.790"
                    + "&getType=json";

            Map<String, Object> response = restTemplate.getForObject(new URI(url), Map.class);

            Object bodyObj = response.get("body");
            if (bodyObj == null) {
                log.warn("[TRAFFIC_FLOW] 노선 {} {} — body 없음", routeNo, drcType);
                return result;
            }

            Map<String, Object> body = (Map<String, Object>) bodyObj;
            List<Map<String, Object>> items = (List<Map<String, Object>>) body.get("items");

            if (items == null || items.isEmpty()) {
                return result;
            }

            for (Map<String, Object> item : items) {
                try {
                    TrafficFlowLogDTO dto = parseItem(item, routeNo, direction);
                    if (dto != null) {
                        result.add(dto);
                    }
                } catch (Exception e) {
                    log.warn("[TRAFFIC_FLOW] 항목 파싱 실패: {}", e.getMessage());
                }
            }
        } catch (Exception e) {
            log.error("[TRAFFIC_FLOW] 노선 {} {} API 호출 실패: {}", routeNo, drcType, e.getMessage());
        }
        return result;
    }

    private TrafficFlowLogDTO parseItem(Map<String, Object> item, String routeNo, String direction) {
        String linkId = getString(item, "linkId");
        if (linkId == null) {
            return null;
        }

        TrafficFlowLogDTO dto = new TrafficFlowLogDTO();
        dto.setLinkId(linkId);
        dto.setRoadName(getString(item, "roadName"));
        dto.setRouteNo(routeNo);
        dto.setDirection(direction);

        String speedStr = getString(item, "speed");
        if (speedStr != null) {
            BigDecimal speed = new BigDecimal(speedStr);
            dto.setSpeed(speed);
            dto.setCongestionLevel(calcCongestion(speed));
        }

        String createdDate = getString(item, "createdDate");
        if (createdDate != null && createdDate.length() >= 14) {
            dto.setCollectedAt(LocalDateTime.parse(createdDate.substring(0, 14), ITS_DATE_FORMAT));
        } else {
            dto.setCollectedAt(LocalDateTime.now());
        }

        return dto;
    }

    private String calcCongestion(BigDecimal speed) {
        int spd = speed.intValue();
        if (spd >= 60) return "SMOOTH";
        if (spd >= 30) return "SLOW";
        return "CONGESTED";
    }

    private String getString(Map<String, Object> map, String key) {
        Object val = map.get(key);
        return val != null ? val.toString().trim() : null;
    }
}
