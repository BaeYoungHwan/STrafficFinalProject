<template>
  <div class="page-container">
    <h2 class="page-title">데이터 분석</h2>

    <!-- 교통 -->
    <div class="section">
      <h3 class="section-title">교통</h3>
      <div class="chart-row">
        <div class="chart-card wide">
          <div class="chart-label">시간대별 평균 속도 (최근 7일)</div>
          <div class="chart-box"><canvas ref="trafficHourlyRef"></canvas></div>
        </div>
        <div class="chart-card">
          <div class="chart-label">혼잡도 분포</div>
          <div class="chart-box square"><canvas ref="trafficCongestionRef"></canvas></div>
        </div>
      </div>
    </div>

    <!-- 단속 -->
    <div class="section">
      <h3 class="section-title">단속</h3>
      <div class="chart-row triple">
        <div class="chart-card">
          <div class="chart-label">일별 단속 건수 (최근 30일)</div>
          <div class="chart-box"><canvas ref="violationDailyRef"></canvas></div>
        </div>
        <div class="chart-card narrow">
          <div class="chart-label">유형별 단속</div>
          <div class="chart-box square"><canvas ref="violationTypeRef"></canvas></div>
        </div>
      </div>
    </div>

    <!-- 예지보전 -->
    <div class="section">
      <h3 class="section-title">예지보전</h3>
      <div class="chart-row">
        <div class="chart-card">
          <div class="chart-label">장비별 이상 감지 빈도</div>
          <div class="chart-box"><canvas ref="anomalyRef"></canvas></div>
        </div>
        <div class="chart-card narrow">
          <div class="chart-label">위험도 분포</div>
          <div class="chart-box square"><canvas ref="riskRef"></canvas></div>
        </div>
      </div>
    </div>

    <!-- 날씨 -->
    <div class="section">
      <h3 class="section-title">날씨</h3>
      <div class="chart-row">
        <div class="chart-card wide">
          <div class="chart-label">기온/습도 추이 (최근 30일)</div>
          <div class="chart-box"><canvas ref="weatherTrendRef"></canvas></div>
        </div>
        <div class="chart-card narrow">
          <div class="chart-label">현재 날씨</div>
          <div class="stat-cards" v-if="currentWeather">
            <div class="stat-item">
              <span class="stat-value">{{ currentWeather.temperature ?? '-' }}°C</span>
              <span class="stat-label">기온</span>
            </div>
            <div class="stat-item">
              <span class="stat-value">{{ currentWeather.humidity ?? '-' }}%</span>
              <span class="stat-label">습도</span>
            </div>
            <div class="stat-item">
              <span class="stat-value">{{ currentWeather.wind_speed ?? '-' }}m/s</span>
              <span class="stat-label">풍속</span>
            </div>
            <div class="stat-item">
              <span class="stat-value text-sm">{{ currentWeather.collected_at ?? '-' }}</span>
              <span class="stat-label">측정 시각</span>
            </div>
          </div>
          <div v-else class="empty-msg">날씨 데이터 없음</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import Chart from 'chart.js/auto'
import api from '../api'

const COLORS = {
  blue: '#1A6DCC',
  green: '#10B981',
  yellow: '#FBBF24',
  orange: '#F59E0B',
  red: '#EF4444',
  gray: '#9CA3AF',
  purple: '#8B5CF6',
}

const CONGESTION_COLORS = { SMOOTH: COLORS.green, SLOW: COLORS.yellow, CONGESTED: COLORS.red }
const CONGESTION_LABELS = { SMOOTH: '원활', SLOW: '서행', CONGESTED: '정체' }
const RISK_COLORS = { LOW: COLORS.green, MEDIUM: COLORS.yellow, HIGH: COLORS.orange, CRITICAL: COLORS.red }
const RISK_LABELS = { LOW: '정상', MEDIUM: '주의', HIGH: '경고', CRITICAL: '위험' }

const trafficHourlyRef = ref(null)
const trafficCongestionRef = ref(null)
const violationDailyRef = ref(null)
const violationTypeRef = ref(null)
const anomalyRef = ref(null)
const riskRef = ref(null)
const weatherTrendRef = ref(null)

const currentWeather = ref(null)

const charts = []

function addChart(c) { if (c) charts.push(c) }

async function fetchAndDraw() {
  const [
    hourly, congestion, daily, vType,
    anomaly, risk, wTrend, wCurrent
  ] = await Promise.allSettled([
    api.get('/statistics/traffic/hourly'),
    api.get('/statistics/traffic/congestion'),
    api.get('/statistics/violation/daily'),
    api.get('/statistics/violation/type'),
    api.get('/statistics/predictive/anomaly'),
    api.get('/statistics/predictive/risk'),
    api.get('/statistics/weather/trend'),
    api.get('/statistics/weather/current'),
  ])

  await nextTick()

  const d = (r) => r.status === 'fulfilled' ? (r.value.data?.data || []) : []

  // 교통 - 시간대별
  const h = d(hourly)
  if (h.length && trafficHourlyRef.value) {
    addChart(new Chart(trafficHourlyRef.value, {
      type: 'line',
      data: {
        labels: h.map(r => r.hour + '시'),
        datasets: [{
          label: '평균 속도 (km/h)',
          data: h.map(r => r.avg_speed),
          borderColor: COLORS.blue,
          backgroundColor: COLORS.blue + '20',
          fill: true, tension: 0.4, pointRadius: 3,
        }],
      },
      options: chartOpts('km/h'),
    }))
  }

  // 교통 - 혼잡도
  const c = d(congestion)
  if (c.length && trafficCongestionRef.value) {
    addChart(new Chart(trafficCongestionRef.value, {
      type: 'doughnut',
      data: {
        labels: c.map(r => CONGESTION_LABELS[r.label] || r.label),
        datasets: [{
          data: c.map(r => r.value),
          backgroundColor: c.map(r => CONGESTION_COLORS[r.label] || COLORS.gray),
        }],
      },
      options: doughnutOpts(),
    }))
  }

  // 단속 - 일별
  const dd = d(daily)
  if (dd.length && violationDailyRef.value) {
    addChart(new Chart(violationDailyRef.value, {
      type: 'bar',
      data: {
        labels: dd.map(r => r.label),
        datasets: [{
          label: '단속 건수',
          data: dd.map(r => r.value),
          backgroundColor: COLORS.red + '80',
          borderRadius: 4,
        }],
      },
      options: chartOpts('건'),
    }))
  }

  // 단속 - 유형별
  const vt = d(vType)
  if (vt.length && violationTypeRef.value) {
    addChart(new Chart(violationTypeRef.value, {
      type: 'doughnut',
      data: {
        labels: vt.map(r => r.label),
        datasets: [{
          data: vt.map(r => r.value),
          backgroundColor: [COLORS.red, COLORS.orange, COLORS.yellow, COLORS.purple],
        }],
      },
      options: doughnutOpts(),
    }))
  }


  // 예지보전 - 이상 빈도
  const an = d(anomaly)
  if (an.length && anomalyRef.value) {
    addChart(new Chart(anomalyRef.value, {
      type: 'bar',
      data: {
        labels: an.map(r => r.label),
        datasets: [{
          label: '이상 감지 횟수',
          data: an.map(r => r.value),
          backgroundColor: COLORS.purple + '80',
          borderRadius: 4,
        }],
      },
      options: chartOpts('회'),
    }))
  }

  // 예지보전 - 위험도
  const rk = d(risk)
  if (rk.length && riskRef.value) {
    addChart(new Chart(riskRef.value, {
      type: 'doughnut',
      data: {
        labels: rk.map(r => RISK_LABELS[r.label] || r.label),
        datasets: [{
          data: rk.map(r => r.value),
          backgroundColor: rk.map(r => RISK_COLORS[r.label] || COLORS.gray),
        }],
      },
      options: doughnutOpts(),
    }))
  }

  // 날씨 - 추이
  const wt = d(wTrend)
  if (wt.length && weatherTrendRef.value) {
    addChart(new Chart(weatherTrendRef.value, {
      type: 'line',
      data: {
        labels: wt.map(r => r.label),
        datasets: [
          {
            label: '기온 (°C)',
            data: wt.map(r => r.avg_temp),
            borderColor: COLORS.red,
            backgroundColor: COLORS.red + '15',
            fill: true, tension: 0.4, pointRadius: 2,
            yAxisID: 'y',
          },
          {
            label: '습도 (%)',
            data: wt.map(r => r.avg_humidity),
            borderColor: COLORS.blue,
            backgroundColor: COLORS.blue + '15',
            fill: true, tension: 0.4, pointRadius: 2,
            yAxisID: 'y1',
          },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { position: 'top', labels: { boxWidth: 12, font: { size: 11 } } } },
        scales: {
          x: { ticks: { color: '#9CA3AF', font: { size: 10 }, maxTicksLimit: 15 }, grid: { color: '#F3F4F6' } },
          y: { position: 'left', title: { display: true, text: '°C', color: COLORS.red }, ticks: { color: '#9CA3AF' }, grid: { color: '#F3F4F6' } },
          y1: { position: 'right', title: { display: true, text: '%', color: COLORS.blue }, ticks: { color: '#9CA3AF' }, grid: { display: false } },
        },
      },
    }))
  }

  // 날씨 - 현재
  const wc = d(wCurrent)
  if (wc.length) currentWeather.value = wc[0]
}

function chartOpts(unit) {
  return {
    responsive: true, maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: { callbacks: { label: ctx => ` ${ctx.parsed.y ?? ctx.parsed.x} ${unit}` } },
    },
    scales: {
      x: { ticks: { color: '#9CA3AF', font: { size: 10 }, maxTicksLimit: 12 }, grid: { color: '#F3F4F6' } },
      y: { ticks: { color: '#9CA3AF', font: { size: 10 } }, grid: { color: '#F3F4F6' } },
    },
  }
}

function doughnutOpts() {
  return {
    responsive: true, maintainAspectRatio: false,
    plugins: {
      legend: { position: 'bottom', labels: { boxWidth: 12, padding: 12, font: { size: 11 } } },
    },
  }
}

onMounted(() => fetchAndDraw())
onBeforeUnmount(() => charts.forEach(c => c?.destroy()))
</script>

<style scoped>
.page-container {
  padding: 28px 32px;
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', sans-serif;
  background: #F0F2F5;
  min-height: 100%;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  color: #1A1A2E;
  margin: 0 0 24px 0;
}

.section {
  margin-bottom: 28px;
}

.section-title {
  font-size: 15px;
  font-weight: 700;
  color: #1A1A2E;
  margin: 0 0 14px 0;
  padding-left: 10px;
  border-left: 3px solid #1A6DCC;
}

.chart-row {
  display: flex;
  gap: 16px;
}
.chart-row.triple { }

.chart-card {
  flex: 1;
  background: #fff;
  border-radius: 14px;
  border: 1px solid rgba(0,0,0,0.07);
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
  min-width: 0;
}
.chart-card.wide { flex: 2; }
.chart-card.narrow { flex: 0.8; }

.chart-label {
  font-size: 12px;
  font-weight: 600;
  color: #6B7280;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 12px;
}

.chart-box {
  height: 220px;
  position: relative;
}
.chart-box.square { height: 200px; }
.chart-box canvas {
  width: 100% !important;
  height: 100% !important;
}

.stat-cards {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  padding-top: 8px;
}

.stat-item {
  text-align: center;
  padding: 16px 8px;
  background: #F9FAFB;
  border-radius: 10px;
  border: 1px solid #F3F4F6;
}

.stat-value {
  display: block;
  font-size: 24px;
  font-weight: 800;
  color: #1A1A2E;
  line-height: 1.2;
}
.stat-value.text-sm {
  font-size: 13px;
  font-weight: 600;
}

.stat-label {
  display: block;
  font-size: 11px;
  color: #9CA3AF;
  margin-top: 4px;
}

.empty-msg {
  text-align: center;
  padding: 40px 0;
  color: #9CA3AF;
  font-size: 13px;
}
</style>
