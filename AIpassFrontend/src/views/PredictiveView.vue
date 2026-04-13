<template>
  <div class="page-container">
    <!-- 페이지 헤더 -->
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">설비 예지보전</h2>
        <span class="equipment-count">{{ filteredEquipments.length }}개</span>
      </div>
      <div class="header-filters">
        <select v-model="riskFilter" class="filter-select">
          <option value="">위험도 전체</option>
          <option value="LOW">정상 (LOW)</option>
          <option value="MEDIUM">주의 (MEDIUM)</option>
          <option value="HIGH">경고 (HIGH)</option>
          <option value="CRITICAL">위험 (CRITICAL)</option>
        </select>
        <select v-model="statusFilter" class="filter-select">
          <option value="">상태 전체</option>
          <option value="OPERATIONAL">정상가능</option>
          <option value="REQUESTED">점검요청</option>
          <option value="IN_PROGRESS">점검중</option>
          <option value="REQUIRED">점검요망</option>
        </select>
      </div>
    </div>

    <!-- 메인 콘텐츠 영역 -->
    <div class="content-area" :class="{ 'panel-open': selectedEquipment }">
      <!-- 테이블 영역 -->
      <div class="table-section">
        <div class="table-card">
          <table class="equipment-table">
            <thead>
              <tr>
                <th>No.</th>
                <th>장비 정보</th>
                <th>주요 지표</th>
                <th>위험도</th>
                <th>잔여 수명</th>
                <th>상태</th>
                <th>최근 점검일</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(eq, idx) in filteredEquipments"
                :key="eq.id"
                class="table-row"
                :class="{ selected: selectedEquipment?.id === eq.id }"
                @click="selectEquipment(eq)"
              >
                <td class="col-no">{{ idx + 1 }}</td>
                <td class="col-name">
                  <span class="equipment-name">{{ eq.name }}</span>
                </td>
                <td class="col-metrics">
                  <div class="metric-line">모터 전류: <strong>{{ eq.motorCurrent }}A</strong></div>
                  <div class="metric-line">베어링 진동: <strong>{{ eq.vibration }} m/s²</strong></div>
                </td>
                <td class="col-risk">
                  <span
                    class="risk-badge"
                    :style="{
                      color: RISK_CONFIG[eq.riskLevel].color,
                      background: RISK_CONFIG[eq.riskLevel].bg
                    }"
                  >
                    <span class="risk-dot" :style="{ background: RISK_CONFIG[eq.riskLevel].color }"></span>
                    {{ RISK_CONFIG[eq.riskLevel].label }}
                  </span>
                </td>
                <td class="col-rul">
                  <span
                    class="rul-text"
                    :style="{ color: getRulColor(eq.rul) }"
                  >{{ formatRul(eq.rul) }}</span>
                </td>
                <td class="col-status">
                  <span
                    class="status-tag"
                    :style="{
                      color: STATUS_CONFIG[eq.status].color,
                      background: STATUS_CONFIG[eq.status].bg,
                      borderColor: STATUS_CONFIG[eq.status].color + '40'
                    }"
                  >{{ STATUS_CONFIG[eq.status].label }}</span>
                </td>
                <td class="col-date">{{ eq.lastInspection }}</td>
              </tr>
              <tr v-if="filteredEquipments.length === 0">
                <td colspan="7" class="empty-row">조건에 맞는 설비가 없습니다.</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- 페이지네이션 -->
        <div class="pagination">
          <button class="page-btn">&lt;</button>
          <button class="page-btn active">1</button>
          <button class="page-btn">&gt;</button>
        </div>
      </div>

      <!-- 상세 패널 -->
      <transition name="panel-slide">
        <div v-if="selectedEquipment" class="detail-panel">
          <!-- 패널 헤더 -->
          <div class="panel-header">
            <div class="panel-title-area">
              <span class="panel-equipment-name">{{ selectedEquipment.name }}</span>
              <span
                class="status-tag"
                :style="{
                  color: STATUS_CONFIG[selectedEquipment.status].color,
                  background: STATUS_CONFIG[selectedEquipment.status].bg,
                  borderColor: STATUS_CONFIG[selectedEquipment.status].color + '40'
                }"
              >{{ STATUS_CONFIG[selectedEquipment.status].label }}</span>
            </div>
            <button class="close-btn" @click="closePanel">×</button>
          </div>

          <div class="panel-install-date">설치일: {{ selectedEquipment.installDate }}</div>

          <!-- 메트릭 카드 4개 -->
          <div class="metric-grid">
            <div class="metric-card">
              <div class="metric-label">모터 전류</div>
              <div class="metric-value">{{ selectedEquipment.motorCurrent }} <span class="metric-unit">A</span></div>
            </div>
            <div class="metric-card">
              <div class="metric-label">베어링 진동</div>
              <div class="metric-value">{{ selectedEquipment.vibration }} <span class="metric-unit">m/s²</span></div>
            </div>
            <div class="metric-card">
              <div class="metric-label">온도</div>
              <div class="metric-value">{{ selectedEquipment.temperature }} <span class="metric-unit">°C</span></div>
            </div>
            <div class="metric-card">
              <div class="metric-label">위험도 스코어</div>
              <div
                class="metric-value"
                :style="{ color: RISK_CONFIG[selectedEquipment.riskLevel].color }"
              >{{ selectedEquipment.riskScore.toFixed(2) }}</div>
            </div>
          </div>

          <!-- RUL 예측 섹션 -->
          <div class="rul-section">
            <button
              class="predict-btn"
              :disabled="rulPredicting"
              @click="predictRul"
            >
              <span class="predict-icon">⚡</span>
              {{ rulPredicting ? 'AI 분석 중...' : 'AI 잔여수명 예측' }}
            </button>

            <transition name="fade">
              <div v-if="rulResult" class="rul-result">
                <span
                  class="rul-grade-badge"
                  :style="{
                    color: RISK_CONFIG[rulResult.grade].color,
                    background: RISK_CONFIG[rulResult.grade].bg,
                    borderColor: RISK_CONFIG[rulResult.grade].color + '50'
                  }"
                >{{ rulResult.grade }}</span>
                <span class="rul-days">잔여 수명 약 <strong>{{ rulResult.rul }}</strong>일</span>
              </div>
            </transition>
          </div>

          <!-- 모터전류 차트 -->
          <div class="chart-section">
            <div class="chart-title">모터전류 추이 (A)</div>
            <div class="chart-card">
              <canvas ref="chartMotorRef"></canvas>
            </div>
          </div>

          <!-- 베어링진동 차트 -->
          <div class="chart-section">
            <div class="chart-title">베어링진동 추이 (m/s²)</div>
            <div class="chart-card">
              <canvas ref="chartVibrationRef"></canvas>
            </div>
          </div>
        </div>
      </transition>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, watch, onBeforeUnmount } from 'vue'
import Chart from 'chart.js/auto'

// ── Mock 데이터 ──────────────────────────────────────────────
const MOCK_EQUIPMENTS = [
  { id: 1, name: 'CAM01', riskLevel: 'LOW',      rul: 312, status: 'OPERATIONAL', motorCurrent: 15.2, vibration: 1.2, temperature: 45, riskScore: 0.12, lastInspection: '2026.03.15', installDate: '2023.06.15' },
  { id: 2, name: 'CAM02', riskLevel: 'LOW',      rul: 305, status: 'OPERATIONAL', motorCurrent: 14.8, vibration: 1.5, temperature: 43, riskScore: 0.15, lastInspection: '2026.03.14', installDate: '2023.07.20' },
  { id: 3, name: 'CAM03', riskLevel: 'MEDIUM',   rul: 150, status: 'REQUESTED',   motorCurrent: 18.5, vibration: 3.2, temperature: 62, riskScore: 0.45, lastInspection: '2026.03.12', installDate: '2022.11.10' },
  { id: 4, name: 'CAM04', riskLevel: 'MEDIUM',   rul: 120, status: 'IN_PROGRESS', motorCurrent: 19.1, vibration: 4.0, temperature: 68, riskScore: 0.52, lastInspection: '2026.03.10', installDate: '2022.08.05' },
  { id: 5, name: 'CAM05', riskLevel: 'HIGH',     rul: 30,  status: 'REQUIRED',    motorCurrent: 24.5, vibration: 5.8, temperature: 78, riskScore: 0.74, lastInspection: '2026.03.08', installDate: '2021.12.20' },
  { id: 6, name: 'CAM06', riskLevel: 'CRITICAL', rul: 3,   status: 'REQUIRED',    motorCurrent: 32.1, vibration: 8.5, temperature: 95, riskScore: 0.93, lastInspection: '2026.03.05', installDate: '2021.03.15' },
]

// ── 색상 설정 ─────────────────────────────────────────────────
const RISK_CONFIG = {
  LOW:      { label: '정상', color: '#10B981', bg: 'rgba(16,185,129,0.15)' },
  MEDIUM:   { label: '주의', color: '#FBBF24', bg: 'rgba(251,191,36,0.15)' },
  HIGH:     { label: '경고', color: '#F59E0B', bg: 'rgba(245,158,11,0.15)' },
  CRITICAL: { label: '위험', color: '#EF4444', bg: 'rgba(239,68,68,0.15)'  },
}

const STATUS_CONFIG = {
  OPERATIONAL: { label: '정상가능', color: '#10B981', bg: 'rgba(16,185,129,0.15)' },
  REQUESTED:   { label: '점검요청', color: '#FBBF24', bg: 'rgba(251,191,36,0.15)' },
  IN_PROGRESS: { label: '점검중',   color: '#1A6DCC', bg: 'rgba(26,109,204,0.15)'  },
  REQUIRED:    { label: '점검요망', color: '#EF4444', bg: 'rgba(239,68,68,0.15)'   },
}

// ── 상태 ─────────────────────────────────────────────────────
const riskFilter   = ref('')
const statusFilter = ref('')
const selectedEquipment = ref(null)
const rulPredicting = ref(false)
const rulResult     = ref(null)
const chartMotorRef     = ref(null)
const chartVibrationRef = ref(null)
let chartMotor     = null
let chartVibration = null

// ── computed ─────────────────────────────────────────────────
const filteredEquipments = computed(() => {
  return MOCK_EQUIPMENTS.filter(eq => {
    const riskOk   = !riskFilter.value   || eq.riskLevel === riskFilter.value
    const statusOk = !statusFilter.value || eq.status    === statusFilter.value
    return riskOk && statusOk
  })
})

// ── 유틸 함수 ─────────────────────────────────────────────────
function formatRul(rul) {
  if (rul <= 3)   return '3일 이내'
  if (rul <= 30)  return `약 ${rul}일`
  if (rul <= 180) return `약 ${rul}일`
  return '300일 이상'
}

function getRulColor(rul) {
  if (rul <= 3)   return '#EF4444'
  if (rul <= 30)  return '#F59E0B'
  if (rul <= 180) return '#FBBF24'
  return '#10B981'
}

function generateTimeSeries(baseValue, points = 12) {
  return Array.from({ length: points }, () => {
    const noise = (Math.random() - 0.5) * 0.2 * baseValue
    return parseFloat((baseValue + noise).toFixed(2))
  })
}

function getTimeLabels(points = 12) {
  const labels = []
  const now = new Date()
  for (let i = points - 1; i >= 0; i--) {
    const d = new Date(now.getTime() - i * 60 * 60 * 1000)
    labels.push(d.getHours().toString().padStart(2, '0') + ':00')
  }
  return labels
}

// ── 차트 ─────────────────────────────────────────────────────
function initCharts() {
  if (!selectedEquipment.value) return
  const eq = selectedEquipment.value
  const labels = getTimeLabels(12)

  // 모터전류 차트
  if (chartMotorRef.value) {
    chartMotor = new Chart(chartMotorRef.value, {
      type: 'line',
      data: {
        labels,
        datasets: [{
          label: '모터 전류 (A)',
          data: generateTimeSeries(eq.motorCurrent),
          borderColor: '#1A6DCC',
          backgroundColor: 'rgba(26,109,204,0.12)',
          borderWidth: 2,
          fill: true,
          tension: 0.4,
          pointRadius: 3,
          pointBackgroundColor: '#1A6DCC',
        }],
      },
      options: chartOptions('A'),
    })
  }

  // 베어링진동 차트
  if (chartVibrationRef.value) {
    chartVibration = new Chart(chartVibrationRef.value, {
      type: 'line',
      data: {
        labels,
        datasets: [{
          label: '베어링 진동 (m/s²)',
          data: generateTimeSeries(eq.vibration),
          borderColor: '#F59E0B',
          backgroundColor: 'rgba(245,158,11,0.12)',
          borderWidth: 2,
          fill: true,
          tension: 0.4,
          pointRadius: 3,
          pointBackgroundColor: '#F59E0B',
        }],
      },
      options: chartOptions('m/s²'),
    })
  }
}

function chartOptions(unit) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: '#1E2140',
        titleColor: '#9CA3AF',
        bodyColor: '#F3F4F6',
        callbacks: {
          label: ctx => ` ${ctx.parsed.y} ${unit}`,
        },
      },
    },
    scales: {
      x: {
        ticks: { color: '#9CA3AF', font: { size: 11 } },
        grid:  { color: 'rgba(255,255,255,0.06)' },
      },
      y: {
        ticks: { color: '#9CA3AF', font: { size: 11 } },
        grid:  { color: 'rgba(255,255,255,0.06)' },
      },
    },
  }
}

function destroyCharts() {
  chartMotor?.destroy()
  chartMotor = null
  chartVibration?.destroy()
  chartVibration = null
}

// ── 메서드 ────────────────────────────────────────────────────
function selectEquipment(eq) {
  rulResult.value = null
  rulPredicting.value = false
  selectedEquipment.value = eq
}

function closePanel() {
  destroyCharts()
  selectedEquipment.value = null
  rulResult.value = null
  rulPredicting.value = false
}

function predictRul() {
  if (rulPredicting.value || !selectedEquipment.value) return
  rulPredicting.value = true
  rulResult.value = null
  setTimeout(() => {
    rulPredicting.value = false
    rulResult.value = {
      grade: selectedEquipment.value.riskLevel,
      rul:   selectedEquipment.value.rul,
    }
  }, 2000)
}

// ── watch ─────────────────────────────────────────────────────
watch(selectedEquipment, async (eq) => {
  destroyCharts()
  if (eq) {
    await nextTick()
    initCharts()
  }
})

onBeforeUnmount(() => destroyCharts())
</script>

<style scoped>
/* ── 기본 ────────────────────────────────────────────────── */
.page-container {
  padding: 28px 32px;
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', sans-serif;
  background: #F0F2F5;
  min-height: 100%;
  box-sizing: border-box;
}

/* ── 헤더 ────────────────────────────────────────────────── */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  color: #1A1A2E;
  margin: 0;
}

.equipment-count {
  background: rgba(26, 109, 204, 0.12);
  color: #1A6DCC;
  font-size: 13px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: 20px;
}

.header-filters {
  display: flex;
  gap: 10px;
}

.filter-select {
  padding: 8px 14px;
  border: 1px solid rgba(26, 109, 204, 0.25);
  border-radius: 8px;
  background: #fff;
  color: #374151;
  font-size: 13px;
  cursor: pointer;
  outline: none;
  transition: border-color 0.2s;
}
.filter-select:hover,
.filter-select:focus {
  border-color: #1A6DCC;
}

/* ── 콘텐츠 레이아웃 ─────────────────────────────────────── */
.content-area {
  display: flex;
  gap: 20px;
  align-items: flex-start;
}

.table-section {
  flex: 1;
  min-width: 0;
  transition: flex 0.3s ease;
}

.content-area.panel-open .table-section {
  flex: 0 0 58%;
}

/* ── 테이블 카드 ──────────────────────────────────────────── */
.table-card {
  background: #fff;
  border-radius: 16px;
  border: 1px solid rgba(0, 0, 0, 0.07);
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
}

.equipment-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13.5px;
}

.equipment-table thead tr {
  background: rgba(26, 109, 204, 0.06);
}

.equipment-table th {
  padding: 13px 16px;
  text-align: left;
  font-weight: 600;
  color: #6B7280;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  border-bottom: 1px solid rgba(0, 0, 0, 0.07);
  white-space: nowrap;
}

.table-row {
  cursor: pointer;
  transition: background 0.15s;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.table-row:last-child {
  border-bottom: none;
}

.table-row:hover {
  background: rgba(26, 109, 204, 0.04);
}

.table-row.selected {
  background: rgba(26, 109, 204, 0.10);
  box-shadow: inset 3px 0 0 #1A6DCC;
}

.equipment-table td {
  padding: 14px 16px;
  color: #374151;
  vertical-align: middle;
}

.col-no {
  color: #9CA3AF;
  font-size: 13px;
  width: 48px;
}

.equipment-name {
  font-weight: 600;
  color: #1A1A2E;
  font-size: 14px;
}

.metric-line {
  font-size: 12.5px;
  color: #6B7280;
  line-height: 1.8;
}
.metric-line strong {
  color: #374151;
}

.risk-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 12.5px;
  font-weight: 600;
}

.risk-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}

.rul-text {
  font-weight: 700;
  font-size: 13.5px;
}

.status-tag {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  border: 1px solid transparent;
}

.col-date {
  color: #9CA3AF;
  font-size: 13px;
}

.empty-row {
  text-align: center;
  padding: 48px 0;
  color: #9CA3AF;
  font-size: 14px;
}

/* ── 페이지네이션 ─────────────────────────────────────────── */
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 6px;
  margin-top: 20px;
}

.page-btn {
  width: 34px;
  height: 34px;
  border: 1px solid rgba(0, 0, 0, 0.12);
  border-radius: 8px;
  background: #fff;
  color: #374151;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;
  display: flex;
  align-items: center;
  justify-content: center;
}
.page-btn:hover {
  border-color: #1A6DCC;
  color: #1A6DCC;
}
.page-btn.active {
  background: #1A6DCC;
  color: #fff;
  border-color: #1A6DCC;
  font-weight: 700;
}

/* ── 상세 패널 ────────────────────────────────────────────── */
.detail-panel {
  flex: 0 0 40%;
  background: #1A1A2E;
  border-radius: 16px;
  padding: 24px;
  color: #E5E7EB;
  overflow-y: auto;
  max-height: calc(100vh - 180px);
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.18);
  box-sizing: border-box;
}

/* 패널 슬라이드 트랜지션 */
.panel-slide-enter-active,
.panel-slide-leave-active {
  transition: transform 0.3s ease, opacity 0.3s ease;
}
.panel-slide-enter-from {
  transform: translateX(30px);
  opacity: 0;
}
.panel-slide-leave-to {
  transform: translateX(30px);
  opacity: 0;
}

/* fade 트랜지션 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* ── 패널 내부 ────────────────────────────────────────────── */
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.panel-title-area {
  display: flex;
  align-items: center;
  gap: 10px;
}

.panel-equipment-name {
  font-size: 20px;
  font-weight: 700;
  color: #F9FAFB;
}

.close-btn {
  width: 32px;
  height: 32px;
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.06);
  color: #9CA3AF;
  font-size: 18px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
  line-height: 1;
}
.close-btn:hover {
  background: rgba(239, 68, 68, 0.15);
  color: #EF4444;
  border-color: #EF4444;
}

.panel-install-date {
  font-size: 12.5px;
  color: #6B7280;
  margin-bottom: 20px;
}

/* ── 메트릭 카드 그리드 ───────────────────────────────────── */
.metric-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 24px;
}

.metric-card {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 14px 16px;
}

.metric-label {
  font-size: 11.5px;
  color: #9CA3AF;
  margin-bottom: 6px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.metric-value {
  font-size: 22px;
  font-weight: 700;
  color: #F9FAFB;
  line-height: 1;
}

.metric-unit {
  font-size: 13px;
  font-weight: 400;
  color: #9CA3AF;
}

/* ── RUL 예측 섹션 ────────────────────────────────────────── */
.rul-section {
  margin-bottom: 24px;
}

.predict-btn {
  width: 100%;
  padding: 12px;
  background: linear-gradient(135deg, #1A6DCC, #0F4E9E);
  color: #fff;
  border: none;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: all 0.2s;
  letter-spacing: 0.02em;
}
.predict-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #2278DC, #1A6DCC);
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(26, 109, 204, 0.35);
}
.predict-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.predict-icon {
  font-size: 16px;
}

.rul-result {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 14px;
  padding: 14px 16px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 10px;
}

.rul-grade-badge {
  padding: 4px 12px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 700;
  border: 1px solid transparent;
  letter-spacing: 0.06em;
}

.rul-days {
  font-size: 14px;
  color: #D1D5DB;
}
.rul-days strong {
  color: #F9FAFB;
  font-weight: 700;
}

/* ── 차트 섹션 ────────────────────────────────────────────── */
.chart-section {
  margin-bottom: 20px;
}

.chart-title {
  font-size: 12.5px;
  font-weight: 600;
  color: #9CA3AF;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 10px;
}

.chart-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 12px;
  padding: 16px;
  height: 160px;
  position: relative;
}

.chart-card canvas {
  width: 100% !important;
  height: 100% !important;
}
</style>
