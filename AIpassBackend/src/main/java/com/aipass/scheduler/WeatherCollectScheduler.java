package com.aipass.scheduler;

import com.aipass.dao.WeatherLogMapper;
import com.aipass.dto.WeatherLogDTO;
import com.aipass.service.ItsCollectLogService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

@Component
public class WeatherCollectScheduler {

    private static final Logger log = LoggerFactory.getLogger(WeatherCollectScheduler.class);
    private static final DateTimeFormatter TM_FORMAT = DateTimeFormatter.ofPattern("yyyyMMddHHmm");

    private static final String DEFAULT_STN = "201";          // 강화
    private static final long DEFAULT_INTERSECTION_ID = 1L;

    private final RestTemplate restTemplate;
    private final WeatherLogMapper weatherLogMapper;
    private final ItsCollectLogService collectLogService;

    @Value("${weather.api.key}")
    private String apiKey;

    @Value("${weather.api.base-url}")
    private String baseUrl;

    public WeatherCollectScheduler(RestTemplate restTemplate,
                                   WeatherLogMapper weatherLogMapper,
                                   ItsCollectLogService collectLogService) {
        this.restTemplate = restTemplate;
        this.weatherLogMapper = weatherLogMapper;
        this.collectLogService = collectLogService;
    }

    /**
     * 5분마다 실행
     */
    @Scheduled(cron = "0 */5 * * * *")
    public void collect() {
        log.info("[WEATHER] 수집 시작");
        try {
            LocalDateTime now = LocalDateTime.now();
            String tm = now.withMinute(0).withSecond(0).format(TM_FORMAT);

            String url = baseUrl + "?tm=" + tm
                    + "&stn=" + DEFAULT_STN
                    + "&help=0"
                    + "&authKey=" + apiKey;

            String response = restTemplate.getForObject(url, String.class);

            if (response == null || response.isBlank()) {
                collectLogService.logFail("WEATHER", "빈 응답");
                return;
            }

            // 데이터 행 추출 (#으로 시작하지 않는 비어있지 않은 행)
            String dataLine = null;
            for (String line : response.split("\n")) {
                String trimmed = line.trim();
                if (!trimmed.isEmpty() && !trimmed.startsWith("#")) {
                    dataLine = trimmed;
                    break;
                }
            }

            if (dataLine == null) {
                collectLogService.logSuccess("WEATHER", 0, 0);
                log.info("[WEATHER] 데이터 없음 — stn:{}, tm:{}", DEFAULT_STN, tm);
                return;
            }

            String[] tokens = dataLine.split("\\s+");
            // 최소 33개 필드 필요 (VS가 33번째)
            if (tokens.length < 33) {
                collectLogService.logFail("WEATHER", "필드 부족: " + tokens.length);
                return;
            }

            WeatherLogDTO dto = new WeatherLogDTO();
            dto.setIntersectionId(DEFAULT_INTERSECTION_ID);

            // 1. TM → collected_at
            dto.setCollectedAt(LocalDateTime.parse(tokens[0], TM_FORMAT));

            // 3. WD (풍향, 36방위) → wind_direction
            int wd = parseIntOrMissing(tokens[2]);
            if (wd != -9) {
                dto.setWindDirection(wd36ToCompass(wd));
            }

            // 4. WS (풍속 m/s) → wind_speed
            BigDecimal ws = parseDecimalOrMissing(tokens[3]);
            if (ws != null) {
                dto.setWindSpeed(ws);
            }

            // 12. TA (기온 ℃) → temperature
            BigDecimal ta = parseDecimalOrMissing(tokens[11]);
            if (ta != null) {
                dto.setTemperature(ta);
            }

            // 14. HM (상대습도 %) → humidity
            BigDecimal hm = parseDecimalOrMissing(tokens[13]);
            if (hm != null) {
                dto.setHumidity(hm.intValue());
            }

            // 16. RN (강수량 mm) → precipitation
            BigDecimal rn = parseDecimalOrMissing(tokens[15]);
            dto.setPrecipitation(rn != null ? rn : BigDecimal.ZERO);

            // 16. RN 기반 → precipitation_type
            if (rn != null && rn.compareTo(BigDecimal.ZERO) > 0) {
                dto.setPrecipitationType("RAIN");
            } else {
                dto.setPrecipitationType("NONE");
            }

            // 26. CA_TOT (전운량 0~10) → sky_condition
            int caTot = parseIntOrMissing(tokens[25]);
            dto.setSkyCondition(cloudToSky(caTot));

            // 33. VS (시정, 10m 단위) → visibility (m)
            int vs = parseIntOrMissing(tokens[32]);
            if (vs != -9) {
                dto.setVisibility(vs * 10);
            }

            weatherLogMapper.insert(dto);
            collectLogService.logSuccess("WEATHER", 1, 1);
            log.info("[WEATHER] 수집 완료 — stn:{}, tm:{}, temp:{}, hm:{}", DEFAULT_STN, tm, dto.getTemperature(), dto.getHumidity());

        } catch (Exception e) {
            collectLogService.logFail("WEATHER", e.getMessage());
            log.error("[WEATHER] 수집 실패", e);
        }
    }

    /** 36방위 → 16방위 문자열 변환 */
    private String wd36ToCompass(int wd36) {
        if (wd36 <= 0 || wd36 > 36) return null;
        String[] dirs = {
                "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"
        };
        // 36방위: 1=10도 간격, 16방위: 22.5도 간격
        double degree = wd36 * 10.0;
        int index = (int) Math.round(degree / 22.5) % 16;
        return dirs[index];
    }

    /** 전운량(0~10) → sky_condition 문자열 */
    private String cloudToSky(int caTot) {
        if (caTot == -9) return null;
        if (caTot <= 2) return "CLEAR";
        if (caTot <= 5) return "PARTLY_CLOUDY";
        if (caTot <= 8) return "MOSTLY_CLOUDY";
        return "OVERCAST";
    }

    /** 결측값(-9) 처리된 정수 파싱 */
    private int parseIntOrMissing(String token) {
        try {
            int val = (int) Double.parseDouble(token);
            return val == -9 ? -9 : val;
        } catch (NumberFormatException e) {
            return -9;
        }
    }

    /** 결측값(-9.0) 처리된 소수 파싱, 결측이면 null 반환 */
    private BigDecimal parseDecimalOrMissing(String token) {
        try {
            BigDecimal val = new BigDecimal(token);
            return val.doubleValue() == -9.0 ? null : val;
        } catch (NumberFormatException e) {
            return null;
        }
    }
}
