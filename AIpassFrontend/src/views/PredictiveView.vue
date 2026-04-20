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
          <option v-for="opt in RISK_FILTER_OPTIONS" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
        </select>
        <select v-model="statusFilter" class="filter-select">
          <option v-for="opt in STATUS_FILTER_OPTIONS" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
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
                      color: getRiskConfig(eq.riskLevel).color,
                      background: getRiskConfig(eq.riskLevel).bg
                    }"
                  >
                    <span class="risk-dot" :style="{ background: getRiskConfig(eq.riskLevel).color }"></span>
                    {{ getRiskConfig(eq.riskLevel).label }}
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
                      color: getStatusConfig(eq.status).color,
                      background: getStatusConfig(eq.status).bg,
                      borderColor: getStatusConfig(eq.status).color + '40'
                    }"
                  >{{ getStatusConfig(eq.status).label }}</span>
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
                  color: getStatusConfig(selectedEquipment.status).color,
                  background: getStatusConfig(selectedEquipment.status).bg,
                  borderColor: getStatusConfig(selectedEquipment.status).color + '40'
                }"
              >{{ getStatusConfig(selectedEquipment.status).label }}</span>
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
                :style="{ color: getRiskConfig(selectedEquipment.riskLevel).color }"
              >{{ selectedEquipment.riskScore != null ? selectedEquipment.riskScore.toFixed(2) : 'N/A' }}</div>
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
                    color: getRiskConfig(rulResult.grade).color,
                    background: getRiskConfig(rulResult.grade).bg,
                    borderColor: getRiskConfig(rulResult.grade).color + '50'
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
import { ref, computed, nextTick, watch, onBeforeUnmount, onMounted } from 'vue'
import Chart from 'chart.js/auto'
import api from '../api'
import { getRiskConfig, getStatusConfig, formatRul, getRulColor, RISK_FILTER_OPTIONS, STATUS_FILTER_OPTIONS } from '../constants/predictive'

// ── 서버 데이터 ───────────────────────────────────────────────
const equipments = ref([])
const loading    = ref(false)
const loadError  = ref(null)

async function fetchEquipments() {
  loading.value = true
  loadError.value = null
  try {
    const res = await api.get('/predictive/equipments')
    if (res.data?.success) {
      equipments.value = res.data.data || []
    } else {
      loadError.value = res.data?.message || '장비 목록 조회 실패'
      equipments.value = []
    }
  } catch (e) {
    loadError.value = e.response?.data?.message || e.message || '네트워크 오류'
    equipments.value = []
  } finally {
    loading.value = false
  }
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
  return equipments.value.filter(eq => {
    const riskOk   = !riskFilter.value   || eq.riskLevel === riskFilter.value
    const statusOk = !statusFilter.value || eq.status    === statusFilter.value
    return riskOk && statusOk
  })
})

// ── 센서 이력 조회 ────────────────────────────────────────────
const sensorHistory = ref([])

async function fetchSensorHistory(equipmentId) {
  try {
    const res = await api.get(`/predictive/equipments/${equipmentId}/sensor-history?hours=12`)
    sensorHistory.value = res.data?.success ? (res.data.data || []) : []
  } catch (e) {
    sensorHistory.value = []
  }
}

// ── 차트 ─────────────────────────────────────────────────────
async function initCharts() {
  if (!selectedEquipment.value) return
  const eq = selectedEquipment.value

  await fetchSensorHistory(eq.id)
  const history = sensorHistory.value

  if (history.length === 0) return

  const labels = history.map(d => {
    const t = String(d.recorded_at || d.recordedAt || '')
    return t.substring(11, 16)
  })

  if (chartMotorRef.value) {
    chartMotor = new Chart(chartMotorRef.value, {
      type: 'line',
      data: {
        labels,
        datasets: [{
          label: '모터 전류 (A)',
          data: history.map(d => d.motor_current ?? d.motorCurrent),
          borderColor: '#1A6DCC',
          backgroundColor: 'rgba(26,109,204,0.12)',
          borderWidth: 2,
          fill: true,
          tension: 0.4,
          pointRadius: 2,
          pointBackgroundColor: '#1A6DCC',
        }],
      },
      options: chartOptions('A'),
    })
  }

  if (chartVibrationRef.value) {
    chartVibration = new Chart(chartVibrationRef.value, {
      type: 'line',
      data: {
        labels,
        datasets: [{
          label: '베어링 진동 (m/s²)',
          data: history.map(d => d.vibration),
          borderColor: '#F59E0B',
          backgroundColor: 'rgba(245,158,11,0.12)',
          borderWidth: 2,
          fill: true,
          tension: 0.4,
          pointRadius: 2,
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

async function predictRul() {
  if (rulPredicting.value || !selectedEquipment.value) return
  rulPredicting.value = true
  rulResult.value = null
  try {
    const eq = selectedEquipment.value
    const res = await api.post('/predictive/predict', {
      items: [{
        equipmentId: eq.id,
        vibration: eq.vibration ?? 0,
        temperature: eq.temperature ?? 0,
        motorCurrent: eq.motorCurrent ?? 0,
      }]
    })
    if (res.data?.success && res.data.data?.length > 0) {
      const pred = res.data.data[0]
      rulResult.value = {
        grade: pred.risk_level || pred.riskLevel || eq.riskLevel,
        rul: eq.rul,
      }
    } else {
      rulResult.value = { grade: eq.riskLevel, rul: eq.rul }
    }
  } catch (e) {
    rulResult.value = {
      grade: selectedEquipment.value?.riskLevel || 'LOW',
      rul: selectedEquipment.value?.rul || 0,
    }
  } finally {
    rulPredicting.value = false
  }
}

// ── watch ─────────────────────────────────────────────────────
watch(selectedEquipment, async (eq) => {
  destroyCharts()
  if (eq) {
    await nextTick()
    await initCharts()
  }
})

// ── lifecycle ────────────────────────────────────────────────
onMounted(() => {
  fetchEquipments()
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
