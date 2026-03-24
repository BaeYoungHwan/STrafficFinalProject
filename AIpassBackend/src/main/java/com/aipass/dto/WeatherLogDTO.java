package com.aipass.dto;

import java.math.BigDecimal;
import java.time.LocalDateTime;

public class WeatherLogDTO {
    private Long weatherId;
    private Long intersectionId;
    private BigDecimal temperature;
    private Integer humidity;
    private BigDecimal windSpeed;
    private String windDirection;
    private BigDecimal precipitation;
    private String precipitationType;
    private String skyCondition;
    private Integer visibility;
    private LocalDateTime collectedAt;
    private LocalDateTime createdAt;

    public WeatherLogDTO() {}

    public Long getWeatherId() { return weatherId; }
    public void setWeatherId(Long weatherId) { this.weatherId = weatherId; }

    public Long getIntersectionId() { return intersectionId; }
    public void setIntersectionId(Long intersectionId) { this.intersectionId = intersectionId; }

    public BigDecimal getTemperature() { return temperature; }
    public void setTemperature(BigDecimal temperature) { this.temperature = temperature; }

    public Integer getHumidity() { return humidity; }
    public void setHumidity(Integer humidity) { this.humidity = humidity; }

    public BigDecimal getWindSpeed() { return windSpeed; }
    public void setWindSpeed(BigDecimal windSpeed) { this.windSpeed = windSpeed; }

    public String getWindDirection() { return windDirection; }
    public void setWindDirection(String windDirection) { this.windDirection = windDirection; }

    public BigDecimal getPrecipitation() { return precipitation; }
    public void setPrecipitation(BigDecimal precipitation) { this.precipitation = precipitation; }

    public String getPrecipitationType() { return precipitationType; }
    public void setPrecipitationType(String precipitationType) { this.precipitationType = precipitationType; }

    public String getSkyCondition() { return skyCondition; }
    public void setSkyCondition(String skyCondition) { this.skyCondition = skyCondition; }

    public Integer getVisibility() { return visibility; }
    public void setVisibility(Integer visibility) { this.visibility = visibility; }

    public LocalDateTime getCollectedAt() { return collectedAt; }
    public void setCollectedAt(LocalDateTime collectedAt) { this.collectedAt = collectedAt; }

    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
}
