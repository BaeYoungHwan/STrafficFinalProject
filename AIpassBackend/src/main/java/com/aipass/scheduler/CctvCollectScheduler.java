package com.aipass.scheduler;

import com.aipass.dao.CctvInfoMapper;
import com.aipass.dto.CctvInfoDTO;
import com.aipass.service.ItsCollectLogService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.net.URI;
import java.util.List;
import java.util.Map;

@Component
public class CctvCollectScheduler {

    private static final Logger log = LoggerFactory.getLogger(CctvCollectScheduler.class);

    private final RestTemplate restTemplate;
    private final CctvInfoMapper cctvInfoMapper;
    private final ItsCollectLogService collectLogService;

    @Value("${its.api.key}")
    private String apiKey;

    @Value("${its.api.base-url}")
    private String baseUrl;

    public CctvCollectScheduler(RestTemplate restTemplate,
                                CctvInfoMapper cctvInfoMapper,
                                ItsCollectLogService collectLogService) {
        this.restTemplate = restTemplate;
        this.cctvInfoMapper = cctvInfoMapper;
        this.collectLogService = collectLogService;
    }

    @Scheduled(cron = "0 0 * * * *")
    public void collect() {
        log.info("[CCTV_INFO] 수집 시작");
        try {
            String url = baseUrl + "/cctvInfo"
                    + "?apiKey=" + apiKey
                    + "&type=its"
                    + "&cctvType=1"
                    + "&minX=126.350&maxX=126.530"
                    + "&minY=37.720&maxY=37.790"
                    + "&getType=json";

            Map<String, Object> response = restTemplate.getForObject(new URI(url), Map.class);

            Object dataObj = response.get("response");
            if (dataObj == null) {
                collectLogService.logFail("CCTV_INFO", "응답에 response 필드 없음");
                return;
            }

            Map<String, Object> responseBody = (Map<String, Object>) dataObj;
            List<Map<String, Object>> dataList = (List<Map<String, Object>>) responseBody.get("data");

            if (dataList == null || dataList.isEmpty()) {
                collectLogService.logSuccess("CCTV_INFO", 0, 0);
                return;
            }

            int totalCount = dataList.size();
            int newCount = 0;

            for (Map<String, Object> item : dataList) {
                try {
                    CctvInfoDTO dto = parseItem(item);
                    if (dto != null) {
                        cctvInfoMapper.upsert(dto);
                        newCount++;
                    }
                } catch (Exception e) {
                    log.warn("[CCTV_INFO] 항목 파싱 실패: {}", e.getMessage());
                }
            }

            collectLogService.logSuccess("CCTV_INFO", totalCount, newCount);
            log.info("[CCTV_INFO] 수집 완료 — 전체: {}건, 저장: {}건", totalCount, newCount);

        } catch (Exception e) {
            collectLogService.logFail("CCTV_INFO", e.getMessage());
            log.error("[CCTV_INFO] 수집 실패", e);
        }
    }

    private CctvInfoDTO parseItem(Map<String, Object> item) {
        String cctvUrl = (String) item.get("cctvurl");
        if (cctvUrl == null || cctvUrl.isBlank()) {
            return null;
        }

        String cctvId = extractCctvId(cctvUrl);
        if (cctvId == null) {
            return null;
        }

        CctvInfoDTO dto = new CctvInfoDTO();
        dto.setCctvId(cctvId);
        String cctvName = (String) item.get("cctvname");
        dto.setCctvName(cctvName);
        dto.setStreamUrl(cctvUrl);

        // cctvName 패턴: [국도48호선] 강화 강화대교 → road_name, district 파싱
        if (cctvName != null) {
            parseCctvName(dto, cctvName);
        }

        Object coordx = item.get("coordx");
        Object coordy = item.get("coordy");
        if (coordx != null) {
            dto.setLongitude(Double.parseDouble(coordx.toString()));
        }
        if (coordy != null) {
            dto.setLatitude(Double.parseDouble(coordy.toString()));
        }

        dto.setIsActive(true);
        return dto;
    }

    private void parseCctvName(CctvInfoDTO dto, String cctvName) {
        // "[국도48호선] 강화 강화대교" → roadName="국도48호선", district="강화"
        int start = cctvName.indexOf('[');
        int end = cctvName.indexOf(']');
        if (start != -1 && end > start) {
            dto.setRoadName(normalizeRoadName(cctvName.substring(start + 1, end).trim()));
            String rest = cctvName.substring(end + 1).trim();
            int spaceIdx = rest.indexOf(' ');
            if (spaceIdx > 0) {
                dto.setDistrict(rest.substring(0, spaceIdx));
            } else if (!rest.isEmpty()) {
                dto.setDistrict(rest);
            }
        }
    }

    /** "국도 48호선", "국도48", "국도48호선" → "국도48호선" 으로 통일 */
    private String normalizeRoadName(String raw) {
        // 공백 제거: "국도 48호선" → "국도48호선"
        String normalized = raw.replaceAll("\\s+", "");
        // "호선" 누락 보정: "국도48" → "국도48호선"
        if (!normalized.endsWith("호선") && normalized.matches(".*\\d$")) {
            normalized += "호선";
        }
        return normalized;
    }

    private String extractCctvId(String cctvUrl) {
        try {
            URI uri = new URI(cctvUrl);
            String path = uri.getPath();
            if (path != null && path.length() > 1) {
                String[] segments = path.substring(1).split("/");
                if (segments.length > 0 && !segments[0].isBlank()) {
                    return segments[0];
                }
            }
        } catch (Exception e) {
            log.warn("[CCTV_INFO] URL 파싱 실패: {}", cctvUrl);
        }
        return null;
    }
}
