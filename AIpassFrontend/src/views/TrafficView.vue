<template>
  <div class="traffic-page">
    <h1 class="page-title">교통 / 신호 제어</h1>

    <!-- 요약 카드 -->
    <div class="summary-cards">
      <div class="summary-card">
        <div class="summary-icon total">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="12" x2="16" y2="12"/></svg>
        </div>
        <div class="summary-info">
          <span class="summary-value">{{ summary.totalIntersections }}</span>
          <span class="summary-label">전체 교차로</span>
        </div>
      </div>
      <div class="summary-card">
        <div class="summary-icon normal">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
        </div>
        <div class="summary-info">
          <span class="summary-value">{{ summary.normalCount }}</span>
          <span class="summary-label">정상 운영</span>
        </div>
      </div>
      <div class="summary-card">
        <div class="summary-icon caution">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
        </div>
        <div class="summary-info">
          <span class="summary-value">{{ summary.cautionCount + summary.emergencyCount }}</span>
          <span class="summary-label">이상 신호</span>
        </div>
      </div>
      <div class="summary-card">
        <div class="summary-icon congested">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="1" y="3" width="15" height="13"/><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/></svg>
        </div>
        <div class="summary-info">
          <span class="summary-value">{{ summary.congestedCount }}</span>
          <span class="summary-label">혼잡 구간</span>
        </div>
      </div>
    </div>

    <div class="traffic-body">
      <!-- 좌: 교차로 목록 -->
      <div class="card intersection-list-card">
        <div class="card-header">
          <h2 class="card-title">교차로 목록</h2>
        </div>
        <div class="intersection-list">
          <div
            v-for="item in intersections"
            :key="item.id"
            class="intersection-item"
            :class="{ selected: selectedId === item.id }"
            @click="selectIntersection(item.id)"
          >
            <div class="item-status">
              <span class="status-dot" :class="item.status.toLowerCase()"></span>
            </div>
            <div class="item-info">
              <span class="item-name">{{ item.name }}</span>
              <span class="item-location">{{ item.location }}</span>
            </div>
            <div class="item-badges">
              <span class="badge-congestion" :class="item.congestion.toLowerCase()">
                {{ congestionLabel(item.congestion) }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- 우: 상세 정보 -->
      <div class="detail-area">
        <template v-if="selected">
          <!-- 신호 제어 패널 -->
          <div class="card signal-card">
            <div class="card-header">
              <h2 class="card-title">{{ selected.name }} — 신호 현시</h2>
              <span class="status-badge" :class="selected.status.toLowerCase()">
                {{ statusLabel(selected.status) }}
              </span>
            </div>

            <div class="signal-body">
              <!-- 신호등 시각화 -->
              <div class="signal-visual">
                <div class="traffic-light">
                  <div class="light red" :class="{ on: selected.currentPhase === 3 }"></div>
                  <div class="light yellow" :class="{ on: selected.currentPhase === 2 }"></div>
                  <div class="light green" :class="{ on: selected.currentPhase === 1 }"></div>
                </div>
                <div class="phase-info">
                  <span class="phase-label">현재 단계</span>
                  <span class="phase-name" :class="currentPhaseClass">{{ currentPhaseLabel }}</span>
                  <span class="phase-remaining">잔여 {{ selected.phaseRemaining }}초</span>
                </div>
              </div>

              <!-- 신호 시간 설정 -->
              <div class="signal-settings">
                <h3 class="settings-title">신호 시간 설정</h3>
                <div class="setting-row">
                  <label>녹색</label>
                  <div class="setting-input">
                    <input v-model.number="signalForm.greenTime" type="number" min="10" max="120" />
                    <span class="unit">초</span>
                  </div>
                  <div class="setting-bar">
                    <div class="bar green-bar" :style="{ width: greenPercent + '%' }"></div>
                  </div>
                </div>
                <div class="setting-row">
                  <label>황색</label>
                  <div class="setting-input">
                    <input v-model.number="signalForm.yellowTime" type="number" min="3" max="10" />
                    <span class="unit">초</span>
                  </div>
                  <div class="setting-bar">
                    <div class="bar yellow-bar" :style="{ width: yellowPercent + '%' }"></div>
                  </div>
                </div>
                <div class="setting-row">
                  <label>적색</label>
                  <div class="setting-input">
                    <input v-model.number="signalForm.redTime" type="number" min="10" max="120" />
                    <span class="unit">초</span>
                  </div>
                  <div class="setting-bar">
                    <div class="bar red-bar" :style="{ width: redPercent + '%' }"></div>
                  </div>
                </div>
                <div class="setting-total">
                  총 주기: <strong>{{ totalCycle }}초</strong>
                </div>
                <p v-if="signalError" class="msg error">{{ signalError }}</p>
                <p v-if="signalSuccess" class="msg success">{{ signalSuccess }}</p>
                <button class="btn-apply" :disabled="signalLoading" @click="applySignal">
                  {{ signalLoading ? '적용 중...' : '신호 변경 적용' }}
                </button>
              </div>
            </div>
          </div>

          <!-- 교통량 차트 -->
          <div class="card chart-card">
            <div class="card-header">
              <h2 class="card-title">시간대별 교통량</h2>
            </div>
            <div class="chart-wrap">
              <canvas ref="chartCanvas"></canvas>
            </div>
          </div>

          <!-- 교통 소통 테이블 -->
          <div class="card table-card">
            <div class="card-header">
              <h2 class="card-title">교통 소통 현황</h2>
            </div>
            <div class="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>시간</th>
                    <th>교통량 (대)</th>
                    <th>평균속도 (km/h)</th>
                    <th>소통 상태</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in trafficFlow" :key="row.time">
                    <td>{{ row.time }}</td>
                    <td>{{ row.volume.toLocaleString() }}</td>
                    <td>{{ row.avgSpeed }}</td>
                    <td>
                      <span class="badge-congestion" :class="row.congestion.toLowerCase()">
                        {{ congestionLabel(row.congestion) }}
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </template>

        <div v-else class="empty-state">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#ccc" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
          <p>좌측 목록에서 교차로를 선택하세요.</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import api from '../api'
import { Chart, registerables } from 'chart.js'

Chart.register(...registerables)

const summary = reactive({
  totalIntersections: 0,
  normalCount: 0,
  cautionCount: 0,
  emergencyCount: 0,
  congestedCount: 0
})

const intersections = ref([])
const selectedId = ref(null)
const selected = ref(null)
const trafficFlow = ref([])

// 신호 설정
const signalForm = reactive({ greenTime: 40, yellowTime: 5, redTime: 35 })
const signalLoading = ref(false)
const signalError = ref('')
const signalSuccess = ref('')

// 차트
const chartCanvas = ref(null)
let chartInstance = null

const totalCycle = computed(() => signalForm.greenTime + signalForm.yellowTime + signalForm.redTime)
const greenPercent = computed(() => (signalForm.greenTime / totalCycle.value) * 100)
const yellowPercent = computed(() => (signalForm.yellowTime / totalCycle.value) * 100)
const redPercent = computed(() => (signalForm.redTime / totalCycle.value) * 100)

const currentPhaseLabel = computed(() => {
  if (!selected.value) return ''
  const p = selected.value.currentPhase
  return p === 1 ? '녹색' : p === 2 ? '황색' : '적색'
})

const currentPhaseClass = computed(() => {
  if (!selected.value) return ''
  const p = selected.value.currentPhase
  return p === 1 ? 'phase-green' : p === 2 ? 'phase-yellow' : 'phase-red'
})

const congestionLabel = (c) => {
  return c === 'SMOOTH' ? '원활' : c === 'SLOW' ? '서행' : '혼잡'
}

const statusLabel = (s) => {
  return s === 'NORMAL' ? '정상' : s === 'CAUTION' ? '주의' : '비상'
}

const fetchSummary = async () => {
  try {
    const res = await api.get('/traffic/summary')
    Object.assign(summary, res.data)
  } catch { /* 무시 */ }
}

const fetchIntersections = async () => {
  try {
    const res = await api.get('/traffic/intersections')
    intersections.value = res.data
  } catch { /* 무시 */ }
}

const selectIntersection = async (id) => {
  selectedId.value = id
  signalError.value = ''
  signalSuccess.value = ''

  const item = intersections.value.find(i => i.id === id)
  selected.value = item

  if (item) {
    signalForm.greenTime = item.greenTime
    signalForm.yellowTime = item.yellowTime
    signalForm.redTime = item.redTime
  }

  try {
    const res = await api.get(`/traffic/flow/${id}`)
    trafficFlow.value = res.data
    await nextTick()
    renderChart()
  } catch { /* 무시 */ }
}

const applySignal = async () => {
  signalError.value = ''
  signalSuccess.value = ''

  if (signalForm.greenTime < 10 || signalForm.greenTime > 120) {
    signalError.value = '녹색 신호는 10~120초 범위여야 합니다.'
    return
  }
  if (signalForm.redTime < 10 || signalForm.redTime > 120) {
    signalError.value = '적색 신호는 10~120초 범위여야 합니다.'
    return
  }

  signalLoading.value = true
  try {
    const res = await api.post(`/traffic/intersections/${selectedId.value}/signal`, {
      greenTime: signalForm.greenTime,
      yellowTime: signalForm.yellowTime,
      redTime: signalForm.redTime
    })
    signalSuccess.value = res.data.message || '신호 설정이 변경되었습니다.'
    setTimeout(() => { signalSuccess.value = '' }, 3000)
  } catch (err) {
    signalError.value = err.response?.data?.message || '신호 변경에 실패했습니다.'
  } finally {
    signalLoading.value = false
  }
}

const renderChart = () => {
  if (chartInstance) {
    chartInstance.destroy()
    chartInstance = null
  }
  if (!chartCanvas.value || trafficFlow.value.length === 0) return

  const labels = trafficFlow.value.map(r => r.time)
  const volumes = trafficFlow.value.map(r => r.volume)
  const speeds = trafficFlow.value.map(r => r.avgSpeed)

  chartInstance = new Chart(chartCanvas.value, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        {
          label: '교통량 (대)',
          data: volumes,
          backgroundColor: 'rgba(26, 109, 204, 0.6)',
          borderColor: '#1A6DCC',
          borderWidth: 1,
          borderRadius: 4,
          yAxisID: 'y'
        },
        {
          label: '평균속도 (km/h)',
          data: speeds,
          type: 'line',
          borderColor: '#F59E0B',
          backgroundColor: 'rgba(245, 158, 11, 0.1)',
          borderWidth: 2,
          pointRadius: 3,
          pointBackgroundColor: '#F59E0B',
          tension: 0.3,
          fill: true,
          yAxisID: 'y1'
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { position: 'top', labels: { font: { size: 12 }, usePointStyle: true, padding: 16 } }
      },
      scales: {
        x: { grid: { display: false }, ticks: { font: { size: 11 } } },
        y: {
          position: 'left',
          title: { display: true, text: '교통량 (대)', font: { size: 11 } },
          grid: { color: '#f0f0f0' },
          ticks: { font: { size: 11 } }
        },
        y1: {
          position: 'right',
          title: { display: true, text: '평균속도 (km/h)', font: { size: 11 } },
          grid: { drawOnChartArea: false },
          ticks: { font: { size: 11 } },
          min: 0,
          max: 80
        }
      }
    }
  })
}

onMounted(async () => {
  await Promise.all([fetchSummary(), fetchIntersections()])
  if (intersections.value.length > 0) {
    selectIntersection(intersections.value[0].id)
  }
})

onBeforeUnmount(() => {
  if (chartInstance) {
    chartInstance.destroy()
  }
})
</script>

<style scoped>
.traffic-page {
  max-width: 1400px;
  margin: 0 auto;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  color: #1F3864;
  margin: 0 0 20px 0;
}

/* 요약 카드 */
.summary-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.summary-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 2px 8px rgba(30, 56, 100, 0.06);
}

.summary-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.summary-icon.total { background: #E8F1FB; color: #1A6DCC; }
.summary-icon.normal { background: #d1fae5; color: #10B981; }
.summary-icon.caution { background: #fef3c7; color: #F59E0B; }
.summary-icon.congested { background: #fee2e2; color: #EF4444; }

.summary-info {
  display: flex;
  flex-direction: column;
}

.summary-value {
  font-size: 26px;
  font-weight: 800;
  color: #1A1A2E;
  line-height: 1.1;
}

.summary-label {
  font-size: 13px;
  color: #6B7280;
  margin-top: 2px;
}

/* 본문 레이아웃 */
.traffic-body {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 20px;
  align-items: start;
}

.card {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(30, 56, 100, 0.06);
  overflow: hidden;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid #E2E8F0;
}

.card-title {
  font-size: 15px;
  font-weight: 700;
  color: #1F3864;
  margin: 0;
}

/* 교차로 목록 */
.intersection-list {
  max-height: calc(100vh - 320px);
  overflow-y: auto;
}

.intersection-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 20px;
  cursor: pointer;
  border-bottom: 1px solid #f5f5f5;
  transition: background 0.15s;
}

.intersection-item:hover {
  background: #f8faff;
}

.intersection-item.selected {
  background: #E8F1FB;
  border-left: 3px solid #1A6DCC;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-dot.normal { background: #10B981; }
.status-dot.caution { background: #F59E0B; }
.status-dot.emergency { background: #EF4444; animation: pulse 1.5s infinite; }

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.item-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.item-name {
  font-size: 14px;
  font-weight: 600;
  color: #1A1A2E;
}

.item-location {
  font-size: 11px;
  color: #999;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.badge-congestion {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
}

.badge-congestion.smooth { background: #d1fae5; color: #059669; }
.badge-congestion.slow { background: #fef3c7; color: #d97706; }
.badge-congestion.congested { background: #fee2e2; color: #dc2626; }

.status-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}

.status-badge.normal { background: #d1fae5; color: #059669; }
.status-badge.caution { background: #fef3c7; color: #d97706; }
.status-badge.emergency { background: #fee2e2; color: #dc2626; }

/* 상세 영역 */
.detail-area {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.empty-state {
  background: #fff;
  border-radius: 12px;
  padding: 80px 20px;
  text-align: center;
  color: #999;
  box-shadow: 0 2px 8px rgba(30, 56, 100, 0.06);
}

.empty-state p {
  margin: 16px 0 0 0;
  font-size: 14px;
}

/* 신호 카드 */
.signal-body {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 32px;
  padding: 24px;
}

.signal-visual {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.traffic-light {
  width: 60px;
  background: #2a2a2a;
  border-radius: 30px;
  padding: 10px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.light {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  opacity: 0.2;
  transition: opacity 0.3s;
}

.light.red { background: #EF4444; }
.light.yellow { background: #F59E0B; }
.light.green { background: #10B981; }

.light.on { opacity: 1; box-shadow: 0 0 16px currentColor; }
.light.red.on { box-shadow: 0 0 16px #EF4444; }
.light.yellow.on { box-shadow: 0 0 16px #F59E0B; }
.light.green.on { box-shadow: 0 0 16px #10B981; }

.phase-info {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.phase-label {
  font-size: 11px;
  color: #999;
}

.phase-name {
  font-size: 18px;
  font-weight: 700;
}

.phase-name.phase-green { color: #10B981; }
.phase-name.phase-yellow { color: #F59E0B; }
.phase-name.phase-red { color: #EF4444; }

.phase-remaining {
  font-size: 13px;
  color: #6B7280;
  font-weight: 500;
}

/* 신호 설정 */
.signal-settings {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.settings-title {
  font-size: 14px;
  font-weight: 700;
  color: #1F3864;
  margin: 0;
}

.setting-row {
  display: grid;
  grid-template-columns: 40px 100px 1fr;
  align-items: center;
  gap: 12px;
}

.setting-row label {
  font-size: 13px;
  font-weight: 600;
  color: #6B7280;
}

.setting-input {
  display: flex;
  align-items: center;
  gap: 4px;
}

.setting-input input {
  width: 60px;
  padding: 6px 8px;
  border: 1px solid #E2E8F0;
  border-radius: 6px;
  font-size: 14px;
  text-align: center;
  outline: none;
  color: #1A1A2E;
}

.setting-input input:focus {
  border-color: #1A6DCC;
}

.unit {
  font-size: 12px;
  color: #999;
}

.setting-bar {
  height: 8px;
  background: #f0f0f0;
  border-radius: 4px;
  overflow: hidden;
}

.bar {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s;
}

.green-bar { background: #10B981; }
.yellow-bar { background: #F59E0B; }
.red-bar { background: #EF4444; }

.setting-total {
  font-size: 13px;
  color: #6B7280;
  text-align: right;
  margin-top: 4px;
}

.setting-total strong {
  color: #1A1A2E;
}

.msg {
  font-size: 13px;
  margin: 0;
  font-weight: 500;
}

.msg.error { color: #EF4444; }
.msg.success { color: #10B981; }

.btn-apply {
  padding: 10px 20px;
  background: #1A6DCC;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
  align-self: flex-end;
}

.btn-apply:hover:not(:disabled) {
  background: #1457A8;
}

.btn-apply:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 차트 */
.chart-wrap {
  padding: 20px;
  height: 300px;
}

/* 테이블 */
.table-wrap {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

thead th {
  padding: 12px 16px;
  background: #f8faff;
  font-size: 13px;
  font-weight: 600;
  color: #1F3864;
  text-align: left;
  border-bottom: 2px solid #E2E8F0;
  white-space: nowrap;
}

tbody td {
  padding: 10px 16px;
  font-size: 13px;
  color: #1A1A2E;
  border-bottom: 1px solid #f0f0f0;
}

tbody tr:hover {
  background: #f8faff;
}

@media (max-width: 1024px) {
  .summary-cards {
    grid-template-columns: repeat(2, 1fr);
  }
  .traffic-body {
    grid-template-columns: 1fr;
  }
  .intersection-list {
    max-height: 300px;
  }
}

@media (max-width: 640px) {
  .summary-cards {
    grid-template-columns: 1fr;
  }
  .signal-body {
    grid-template-columns: 1fr;
  }
}
</style>
