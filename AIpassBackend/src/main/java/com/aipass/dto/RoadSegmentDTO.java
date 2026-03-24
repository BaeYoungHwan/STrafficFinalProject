package com.aipass.dto;

public class RoadSegmentDTO {

    private Long fromId;
    private Double fromLat;
    private Double fromLng;
    private Long toId;
    private Double toLat;
    private Double toLng;
    private String congestionLevel;

    public Long getFromId() { return fromId; }
    public void setFromId(Long fromId) { this.fromId = fromId; }

    public Double getFromLat() { return fromLat; }
    public void setFromLat(Double fromLat) { this.fromLat = fromLat; }

    public Double getFromLng() { return fromLng; }
    public void setFromLng(Double fromLng) { this.fromLng = fromLng; }

    public Long getToId() { return toId; }
    public void setToId(Long toId) { this.toId = toId; }

    public Double getToLat() { return toLat; }
    public void setToLat(Double toLat) { this.toLat = toLat; }

    public Double getToLng() { return toLng; }
    public void setToLng(Double toLng) { this.toLng = toLng; }

    public String getCongestionLevel() { return congestionLevel; }
    public void setCongestionLevel(String congestionLevel) { this.congestionLevel = congestionLevel; }
}
