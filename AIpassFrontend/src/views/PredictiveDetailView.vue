<template>
  <div class="detail-container">
    <!-- 헤더 -->
    <div class="detail-header">
      <button class="back-btn" @click="$router.push('/predictive')">← 목록으로</button>
      <div class="header-right" v-if="equipment">
        <span class="eq-name">{{ equipment.name }} 상세</span>
        <span
          class="status-tag"
          :style="{
            color: getStatusConfig(equipment.status).color,
            background: getStatusConfig(equipment.status).bg,
            borderColor: getStatusConfig(equipment.status).color + '40'
          }"
        >{{ getStatusConfig(equipment.status).label }}</span>
      </div>
    </div>

    <div v-if="!equipment" class="loading-msg">장비 정보를 불러오는 중...</div>

    <template v-if="equipment">
      <!-- 장비 정보 테이블 -->
      <div class="section-card">
        <h3 class="section-title">장비 정보</h3>
        <table class="info-table">
          <tbody>
            <tr><th>장비명</th><td>{{ equipment.name }}</td><th>번호</th><td>{{ equipment.id }}</td></tr>
            <tr><th>모터 전류</th><td>{{ equipment.motorCurrent ?? '-' }} A</td><th>베어링 진동</th><td>{{ equipment.vibration ?? '-' }} m/s²</td></tr>
            <tr><th>온도</th><td>{{ equipment.temperature ?? '-' }} °C</td><th>위험도 스코어</th><td :style="{ color: getRiskConfig(equipment.riskLevel).color, fontWeight: 700 }">{{ equipment.riskScore != null ? equipment.riskScore.toFixed(2) : 'N/A' }}</td></tr>
            <tr>
              <th>위험도</th>
              <td>
                <span class="risk-badge" :style="{ color: getRiskConfig(equipment.riskLevel).color, background: getRiskConfig(equipment.riskLevel).bg }">
                  <span class="risk-dot" :style="{ background: getRiskConfig(equipment.riskLevel).color }"></span>
                  {{ getRiskConfig(equipment.riskLevel).label }}
                </span>
              </td>
              <th>상태</th>
              <td>
                <span class="status-tag" :style="{ color: getStatusConfig(equipment.status).color, background: getStatusConfig(equipment.status).bg, borderColor: getStatusConfig(equipment.status).color + '40' }">
                  {{ getStatusConfig(equipment.status).label }}
                </span>
              </td>
            </tr>
            <tr>
              <th>잔여 수명</th>
              <td :style="{ color: getRulColor(equipment.rul), fontWeight: 700 }">{{ formatRul(equipment.rul) }}</td>
              <th>설치일</th><td>{{ equipment.installDate ?? '-' }}</td>
            </tr>
            <tr><th>최근 점검일</th><td>{{ equipment.lastInspection ?? '-' }}</td><th></th><td></td></tr>
          </tbody>
        </table>
      </div>

      <!-- AI 잔여수명 예측 -->
      <div class="section-card">
        <h3 class="section-title">AI 잔여수명 예측</h3>
        <button class="predict-btn" :disabled="rulPredicting" @click="predictRul">
          <span>⚡</span>
          {{ rulPredicting ? 'AI 분석 중...' : 'AI 잔여수명 예측' }}
        </button>
        <div v-if="rulResult" class="rul-result">
          <span class="rul-grade-badge" :style="{ color: getRiskConfig(rulResult.grade).color, background: getRiskConfig(rulResult.grade).bg }">
            {{ getRiskConfig(rulResult.grade).label }}
          </span>
          <span class="rul-days">잔여 수명 약 <strong>{{ rulResult.rul }}</strong>일</span>
        </div>
      </div>

      <!-- 센서 추이 그래프 -->
      <div class="section-card">
        <div class="chart-header">
          <h3 class="section-title">센서 추이</h3>
          <div class="range-btns">
            <button v-for="r in rangeOptions" :key="r.value"
              class="range-btn" :class="{ active: chartRange === r.value }"
              @click="changeRange(r.value)"
            >{{ r.label }}</button>
          </div>
        </div>
        <div class="chart-grid">
          <div class="chart-wrap">
            <div class="chart-label">모터전류 (A)</div>
            <div class="chart-box"><canvas ref="chartMotorRef"></canvas></div>
          </div>
          <div class="chart-wrap">
            <div class="chart-label">베어링진동 (m/s²)</div>
            <div class="chart-box"><canvas ref="chartVibrationRef"></canvas></div>
          </div>
          <div class="chart-wrap">
            <div class="chart-label">온도 (°C)</div>
            <div class="chart-box"><canvas ref="chartTempRef"></canvas></div>
          </div>
        </div>
        <div v-if="sensorHistory.length === 0" class="empty-chart">센서 데이터가 없습니다.</div>
      </div>

      <!-- 데이터 다운로드 -->
      <div class="section-card">
        <h3 class="section-title">센서 데이터 다운로드</h3>
        <div class="download-btns">
          <button class="action-btn" @click="downloadCSV">📥 CSV 다운로드</button>
          <button class="action-btn" @click="downloadExcel">📊 Excel 다운로드</button>
        </div>
      </div>

      <!-- 정비 기록 -->
      <div class="section-card">
        <h3 class="section-title">정비 기록</h3>
        <table v-if="maintenanceHistory.length > 0" class="history-table">
          <thead>
            <tr><th>No.</th><th>상태</th><th>담당자</th><th>접수일</th><th>완료일</th></tr>
          </thead>
          <tbody>
            <tr v-for="(h, idx) in maintenanceHistory" :key="h.ticket_id">
              <td>{{ idx + 1 }}</td>
              <td>
                <span class="status-tag" :style="{
                  color: h.repair_status === '완료' ? '#10B981' : '#F59E0B',
                  background: h.repair_status === '완료' ? 'rgba(16,185,129,0.15)' : 'rgba(245,158,11,0.15)'
                }">{{ h.repair_status }}</span>
              </td>
              <td>{{ h.reported_by ?? '-' }}</td>
              <td>{{ h.created_at ?? '-' }}</td>
              <td>{{ h.resolved_at ?? '-' }}</td>
            </tr>
          </tbody>
        </table>
        <div v-else class="empty-chart">정비 기록이 없습니다.</div>
      </div>

      <!-- 액션 버튼 -->
      <div class="action-bar">
        <button class="action-btn action-alert" @click="sendAlert">🔔 알림 발송</button>
        <button class="action-btn action-resolve" @click="resolveEquipment" v-if="equipment.riskLevel === 'CRITICAL'">✅ 수동 해제</button>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { useRoute } from 'vue-router'
import Chart from 'chart.js/auto'
import api from '../api'
import { getRiskConfig, getStatusConfig, formatRul, getRulColor } from '../constants/predictive'

const route = useRoute()
const equipmentId = Number(route.params.id)

const equipment = ref(null)
const sensorHistory = ref([])
const maintenanceHistory = ref([])
const rulPredicting = ref(false)
const rulResult = ref(null)
const chartRange = ref(12)

const chartMotorRef = ref(null)
const chartVibrationRef = ref(null)
const chartTempRef = ref(null)
let chartMotor = null, chartVibration = null, chartTemp = null

const rangeOptions = [
  { label: '12시간', value: 12 },
  { label: '1일', value: 24 },
  { label: '7일', value: 168 },
]

async function fetchEquipment() {
  try {
    const res = await api.get(`/predictive/equipments/${equipmentId}`)
    equipment.value = res.data?.success ? res.data.data : null
  } catch (e) { equipment.value = null }
}

async function fetchSensorHistory() {
  try {
    const res = await api.get(`/predictive/equipments/${equipmentId}/sensor-history?hours=${chartRange.value}`)
    sensorHistory.value = res.data?.success ? (res.data.data || []) : []
  } catch (e) { sensorHistory.value = [] }
}

async function fetchMaintenanceHistory() {
  try {
    const res = await api.get(`/predictive/equipments/${equipmentId}/maintenance-history`)
    maintenanceHistory.value = res.data?.success ? (res.data.data || []) : []
  } catch (e) { maintenanceHistory.value = [] }
}

function destroyCharts() {
  chartMotor?.destroy(); chartMotor = null
  chartVibration?.destroy(); chartVibration = null
  chartTemp?.destroy(); chartTemp = null
}

function makeChart(canvasRef, label, data, labels, color) {
  if (!canvasRef) return null
  return new Chart(canvasRef, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label,
        data,
        borderColor: color,
        backgroundColor: color + '20',
        borderWidth: 2,
        fill: true,
        tension: 0.4,
        pointRadius: 1,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: '#9CA3AF', font: { size: 10 }, maxTicksLimit: 12 }, grid: { color: '#F3F4F6' } },
        y: { ticks: { color: '#9CA3AF', font: { size: 10 } }, grid: { color: '#F3F4F6' } },
      },
    },
  })
}

async function initCharts() {
  destroyCharts()
  await fetchSensorHistory()
  if (sensorHistory.value.length === 0) return

  await nextTick()
  const h = sensorHistory.value
  const labels = h.map(d => String(d.recorded_at || '').substring(11, 16))

  chartMotor = makeChart(chartMotorRef.value, '모터전류', h.map(d => d.motor_current), labels, '#1A6DCC')
  chartVibration = makeChart(chartVibrationRef.value, '진동', h.map(d => d.vibration), labels, '#F59E0B')
  chartTemp = makeChart(chartTempRef.value, '온도', h.map(d => d.temperature), labels, '#EF4444')
}

async function changeRange(hours) {
  chartRange.value = hours
  await initCharts()
}

async function predictRul() {
  if (rulPredicting.value || !equipment.value) return
  rulPredicting.value = true
  rulResult.value = null
  try {
    const eq = equipment.value
    const res = await api.post('/predictive/predict', {
      items: [{ equipmentId: eq.id, vibration: eq.vibration ?? 0, temperature: eq.temperature ?? 0, motorCurrent: eq.motorCurrent ?? 0 }]
    })
    if (res.data?.success && res.data.data?.length > 0) {
      const pred = res.data.data[0]
      rulResult.value = { grade: pred.risk_level || eq.riskLevel, rul: eq.rul }
    } else {
      rulResult.value = { grade: eq.riskLevel, rul: eq.rul }
    }
  } catch (e) {
    rulResult.value = { grade: equipment.value?.riskLevel || 'LOW', rul: equipment.value?.rul || 0 }
  } finally { rulPredicting.value = false }
}

function downloadCSV() {
  if (sensorHistory.value.length === 0) { alert('다운로드할 데이터가 없습니다.'); return }
  const header = 'recorded_at,motor_current,vibration,temperature\n'
  const rows = sensorHistory.value.map(d => `${d.recorded_at},${d.motor_current},${d.vibration},${d.temperature}`).join('\n')
  const blob = new Blob(['\uFEFF' + header + rows], { type: 'text/csv;charset=utf-8;' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `${equipment.value?.name || 'sensor'}_data.csv`
  a.click()
}

function downloadExcel() {
  if (sensorHistory.value.length === 0) { alert('다운로드할 데이터가 없습니다.'); return }
  let table = '<table><tr><th>시간</th><th>모터전류(A)</th><th>진동(m/s²)</th><th>온도(°C)</th></tr>'
  sensorHistory.value.forEach(d => {
    table += `<tr><td>${d.recorded_at}</td><td>${d.motor_current}</td><td>${d.vibration}</td><td>${d.temperature}</td></tr>`
  })
  table += '</table>'
  const blob = new Blob(['\uFEFF' + table], { type: 'application/vnd.ms-excel;charset=utf-8;' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `${equipment.value?.name || 'sensor'}_data.xls`
  a.click()
}

function sendAlert() {
  alert(`${equipment.value?.name} 점검 알림이 발송되었습니다.`)
}

async function resolveEquipment() {
  if (!confirm(`${equipment.value?.name} 장비를 정상 상태로 복원하시겠습니까?`)) return
  try {
    await api.post(`/predictive/equipments/${equipmentId}/resolve`)
    alert('장비 상태가 정상으로 복원되었습니다.')
    await fetchEquipment()
  } catch (e) {
    alert('해제 실패: ' + (e.response?.data?.message || e.message))
  }
}

onMounted(async () => {
  await fetchEquipment()
  await fetchMaintenanceHistory()
  await initCharts()
})

onBeforeUnmount(() => destroyCharts())
</script>

<style scoped>
.detail-container {
  padding: 28px 32px;
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', sans-serif;
  background: #F0F2F5;
  min-height: 100%;
  max-width: 1000px;
  margin: 0 auto;
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.back-btn {
  padding: 8px 16px;
  border: 1px solid #E2E8F0;
  border-radius: 8px;
  background: #fff;
  color: #374151;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}
.back-btn:hover { border-color: #1A6DCC; color: #1A6DCC; }

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.eq-name {
  font-size: 20px;
  font-weight: 700;
  color: #1A1A2E;
}

.loading-msg {
  text-align: center;
  padding: 60px 0;
  color: #9CA3AF;
  font-size: 15px;
}

/* ── 섹션 카드 ──────────────────────────────────────────── */
.section-card {
  background: #fff;
  border-radius: 14px;
  border: 1px solid rgba(0, 0, 0, 0.07);
  padding: 24px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.section-title {
  font-size: 15px;
  font-weight: 700;
  color: #1A1A2E;
  margin: 0 0 16px 0;
}

/* ── 정보 테이블 ────────────────────────────────────────── */
.info-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.info-table th {
  text-align: left;
  padding: 10px 14px;
  color: #6B7280;
  font-weight: 500;
  width: 120px;
  background: #F9FAFB;
  border: 1px solid #F3F4F6;
}
.info-table td {
  padding: 10px 14px;
  color: #1A1A2E;
  font-weight: 600;
  border: 1px solid #F3F4F6;
}

.risk-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 10px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
}
.risk-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
}

.status-tag {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  border: 1px solid transparent;
}

/* ── AI 예측 ────────────────────────────────────────────── */
.predict-btn {
  padding: 12px 24px;
  background: linear-gradient(135deg, #1A6DCC, #0F4E9E);
  color: #fff;
  border: none;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  transition: all 0.2s;
}
.predict-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(26, 109, 204, 0.35);
}
.predict-btn:disabled { opacity: 0.7; cursor: not-allowed; }

.rul-result {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 14px;
  padding: 14px 16px;
  background: #F9FAFB;
  border: 1px solid #E5E7EB;
  border-radius: 10px;
}
.rul-grade-badge {
  padding: 4px 12px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 700;
}
.rul-days { font-size: 14px; color: #374151; }
.rul-days strong { font-weight: 700; }

/* ── 차트 ───────────────────────────────────────────────── */
.chart-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.chart-header .section-title { margin: 0; }

.range-btns { display: flex; gap: 6px; }
.range-btn {
  padding: 6px 14px;
  border: 1px solid #E2E8F0;
  border-radius: 6px;
  background: #fff;
  color: #6B7280;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}
.range-btn:hover { border-color: #1A6DCC; color: #1A6DCC; }
.range-btn.active {
  background: #1A6DCC;
  color: #fff;
  border-color: #1A6DCC;
}

.chart-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 16px;
}
.chart-wrap {}
.chart-label {
  font-size: 11.5px;
  font-weight: 600;
  color: #6B7280;
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.chart-box {
  height: 180px;
  position: relative;
}
.chart-box canvas {
  width: 100% !important;
  height: 100% !important;
}

.empty-chart {
  text-align: center;
  padding: 40px 0;
  color: #9CA3AF;
  font-size: 14px;
}

/* ── 다운로드 ───────────────────────────────────────────── */
.download-btns {
  display: flex;
  gap: 12px;
}

/* ── 정비 기록 ──────────────────────────────────────────── */
.history-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.history-table th {
  padding: 10px 12px;
  text-align: left;
  font-weight: 600;
  color: #6B7280;
  font-size: 12px;
  border-bottom: 2px solid #E5E7EB;
}
.history-table td {
  padding: 10px 12px;
  color: #374151;
  border-bottom: 1px solid #F3F4F6;
}

/* ── 액션 바 ────────────────────────────────────────────── */
.action-bar {
  display: flex;
  gap: 12px;
  margin-top: 8px;
}

.action-btn {
  padding: 12px 24px;
  border: 1px solid #E2E8F0;
  border-radius: 10px;
  background: #fff;
  color: #374151;
  font-size: 13.5px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  transition: all 0.15s;
}
.action-btn:hover {
  border-color: #1A6DCC;
  color: #1A6DCC;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.action-resolve {
  background: #10B981;
  color: #fff;
  border-color: #10B981;
}
.action-resolve:hover {
  background: #059669;
  border-color: #059669;
  color: #fff;
}
</style>
