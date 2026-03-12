package com.aipass.dto;

import java.util.List;
import java.util.Map;

public class DashboardDto {
    // 기존 필드
    private String linetitle; 
    private String station_id; 
    private int linetotal; 
    private int stationtotal; 
    private int line_stationcount; 
    private int incident_count; 
    private int total_lockers; 
    private int used_lockers; 
    private int hour_usedlocker; 
    private List<Map<String, Object>> weekly_issue; 
    
    // 날씨
    private String weather_tm; 
    private double weather_wd; 
    private double weather_ws; 
    private double weather_ta; 
    private double weather_hm; 
    private double weather_rn; 
    
    // 새로운 필드
    private long todayTrafficTotal;
    private double trafficChangeRate;
    private int unprocessedCount;
    private int riskEquipmentCount;
    private List<Integer> trafficTrend;
    private List<String> recentAlerts;
	public String getLinetitle() {
		return linetitle;
	}
	public void setLinetitle(String linetitle) {
		this.linetitle = linetitle;
	}
	public String getStation_id() {
		return station_id;
	}
	public void setStation_id(String station_id) {
		this.station_id = station_id;
	}
	public int getLinetotal() {
		return linetotal;
	}
	public void setLinetotal(int linetotal) {
		this.linetotal = linetotal;
	}
	public int getStationtotal() {
		return stationtotal;
	}
	public void setStationtotal(int stationtotal) {
		this.stationtotal = stationtotal;
	}
	public int getLine_stationcount() {
		return line_stationcount;
	}
	public void setLine_stationcount(int line_stationcount) {
		this.line_stationcount = line_stationcount;
	}
	public int getIncident_count() {
		return incident_count;
	}
	public void setIncident_count(int incident_count) {
		this.incident_count = incident_count;
	}
	public int getTotal_lockers() {
		return total_lockers;
	}
	public void setTotal_lockers(int total_lockers) {
		this.total_lockers = total_lockers;
	}
	public int getUsed_lockers() {
		return used_lockers;
	}
	public void setUsed_lockers(int used_lockers) {
		this.used_lockers = used_lockers;
	}
	public int getHour_usedlocker() {
		return hour_usedlocker;
	}
	public void setHour_usedlocker(int hour_usedlocker) {
		this.hour_usedlocker = hour_usedlocker;
	}
	public List<Map<String, Object>> getWeekly_issue() {
		return weekly_issue;
	}
	public void setWeekly_issue(List<Map<String, Object>> weekly_issue) {
		this.weekly_issue = weekly_issue;
	}
	public String getWeather_tm() {
		return weather_tm;
	}
	public void setWeather_tm(String weather_tm) {
		this.weather_tm = weather_tm;
	}
	public double getWeather_wd() {
		return weather_wd;
	}
	public void setWeather_wd(double weather_wd) {
		this.weather_wd = weather_wd;
	}
	public double getWeather_ws() {
		return weather_ws;
	}
	public void setWeather_ws(double weather_ws) {
		this.weather_ws = weather_ws;
	}
	public double getWeather_ta() {
		return weather_ta;
	}
	public void setWeather_ta(double weather_ta) {
		this.weather_ta = weather_ta;
	}
	public double getWeather_hm() {
		return weather_hm;
	}
	public void setWeather_hm(double weather_hm) {
		this.weather_hm = weather_hm;
	}
	public double getWeather_rn() {
		return weather_rn;
	}
	public void setWeather_rn(double weather_rn) {
		this.weather_rn = weather_rn;
	}
	public long getTodayTrafficTotal() {
		return todayTrafficTotal;
	}
	public void setTodayTrafficTotal(long todayTrafficTotal) {
		this.todayTrafficTotal = todayTrafficTotal;
	}
	public double getTrafficChangeRate() {
		return trafficChangeRate;
	}
	public void setTrafficChangeRate(double trafficChangeRate) {
		this.trafficChangeRate = trafficChangeRate;
	}
	public int getUnprocessedCount() {
		return unprocessedCount;
	}
	public void setUnprocessedCount(int unprocessedCount) {
		this.unprocessedCount = unprocessedCount;
	}
	public int getRiskEquipmentCount() {
		return riskEquipmentCount;
	}
	public void setRiskEquipmentCount(int riskEquipmentCount) {
		this.riskEquipmentCount = riskEquipmentCount;
	}
	public List<Integer> getTrafficTrend() {
		return trafficTrend;
	}
	public void setTrafficTrend(List<Integer> trafficTrend) {
		this.trafficTrend = trafficTrend;
	}
	public List<String> getRecentAlerts() {
		return recentAlerts;
	}
	public void setRecentAlerts(List<String> recentAlerts) {
		this.recentAlerts = recentAlerts;
	}

    // 게터와 세터 메소드들 추가
    // ...
}