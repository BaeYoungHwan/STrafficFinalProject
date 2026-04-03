<template>
  <div class="predictive">
    <!-- 섹션 헤더 -->
    <div class="section-header">
      <h2 class="section-title">장비 정보 조회</h2>
      <button class="btn-refresh" @click="fetchEquipments" title="새로 고침">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/>
          <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
        </svg>
        새로 고침
      </button>
    </div>

    <!-- 필터 패널 -->
    <div class="filter-panel">
      <div class="filter-row">
        <div class="filter-item">
          <select v-model="filters.equipment">
            <option value="">장비 전체</option>
            <option value="CAM">CAM (카메라)</option>
          </select>
        </div>
        <div class="filter-item">
          <select v-model="filters.riskLevel">
            <option value="">위험도 전체</option>
            <option value="LOW">정상</option>
            <option value="MEDIUM">주의</option>
            <option value="HIGH">경고</option>
            <option value="CRITICAL">위험</option>
          </select>
        </div>
        <div class="filter-item">
          <select v-model="filters.status">
            <option value="">상태 전체</option>
            <option value="정상가동">정상가동</option>
            <option value="통신오류">통신오류</option>
            <option value="점검중">점검중</option>
            <option value="점검요망">점검요망</option>
          </select>
        </div>
        <div class="filter-actions">
          <button class="btn-search" @click="search">검 색</button>
          <button class="btn-reset" @click="reset">초기화</button>
        </div>
      </div>
    </div>

    <!-- 콘텐츠 영역 -->
    <div class="content-area" :class="{ 'has-detail': selectedEquipment }">
      <!-- 목록 -->
      <div class="list-section">
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>No</th>
                <th>장비정보</th>
                <template v-if="!selectedEquipment">
                  <th>모터전류 (A)</th>
                  <th>베어링진동 (mm/s)</th>
                </template>
                <th>위험도</th>
                <template v-if="!selectedEquipment">
                  <th>잔여수명</th>
                </template>
                <th>상태</th>
                <th>최근점검일</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="loading">
                <td :colspan="selectedEquipment ? 5 : 7" class="loading-cell">불러오는 중...</td>
              </tr>
              <tr v-else-if="items.length === 0">
                <td :colspan="selectedEquipment ? 5 : 7" class="empty-cell">장비 데이터가 없습니다.</td>
              </tr>
              <tr
                v-for="(item, index) in items"
                :key="item.equipmentId"
                :class="{ selected: selectedEquipment && selectedEquipment.equipmentId === item.equipmentId }"
                @click="selectEquipment(item)"
              >
                <td>{{ (currentPage - 1) * 20 + index + 1 }}</td>
                <td class="equipment-info-cell">
                  <div class="equipment-name">{{ item.equipmentName }}</div>
                  <div class="equipment-location">{{ item.intersectionName }}</div>
                </td>
                <template v-if="!selectedEquipment">
                  <td>{{ item.motorCurrent != null ? item.motorCurrent.toFixed(2) : '-' }}</td>
                  <td>{{ item.bearingVibration != null ? item.bearingVibration.toFixed(3) : '-' }}</td>
                </template>
                <td>
                  <span class="risk-dot-wrap">
                    <span
                      class="risk-dot"
                      :style="{ background: getRiskColor(item.riskLevel) }"
                    ></span>
                    <span :style="{ color: getRiskColor(item.riskLevel), fontWeight: 600 }">
                      {{ getRiskLabel(item.riskLevel) }}
                    </span>
                  </span>
                </td>
                <template v-if="!selectedEquipment">
                  <td>{{ formatRul(item.rul) }}</td>
                </template>
                <td>
                  <span class="status-badge" :style="getStatusStyle(item.status)">
                    {{ item.status }}
                  </span>
                </td>
                <td>{{ item.lastInspectionDate ?? '-' }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- 페이지네이션 -->
        <div class="pagination">
          <button :disabled="currentPage === 1" @click="changePage(currentPage - 1)">&lt;</button>
          <button
            v-for="p in pageNumbers"
            :key="p"
            :class="{ active: p === currentPage }"
            @click="changePage(p)"
          >{{ p }}</button>
          <button :disabled="currentPage === totalPages" @click="changePage(currentPage + 1)">&gt;</button>
        </div>
      </div>

      <!-- 상세 패널 -->
      <Transition name="slide-in">
        <div class="detail-section" v-if="selectedEquipment">
          <div class="detail-header">
            <span class="detail-title">장비 상세 정보</span>
            <button class="btn-close" @click="selectedEquipment = null">✕</button>
          </div>

          <!-- 위험도 강조 배너 -->
          <div
            class="risk-banner"
            :style="{ background: getRiskBannerBg(selectedEquipment.riskLevel), borderColor: getRiskColor(selectedEquipment.riskLevel) }"
          >
            <span class="risk-banner-dot" :style="{ background: getRiskColor(selectedEquipment.riskLevel) }"></span>
            <span class="risk-banner-label" :style="{ color: getRiskColor(selectedEquipment.riskLevel) }">
              {{ getRiskLabel(selectedEquipment.riskLevel) }}
            </span>
            <span class="risk-banner-rul">잔여수명 {{ formatRul(selectedEquipment.rul) }}</span>
          </div>

          <!-- 상세 정보 테이블 -->
          <table class="detail-table">
            <tbody>
              <tr>
                <th>장비정보</th>
                <td>{{ selectedEquipment.equipmentName }}</td>
              </tr>
              <tr>
                <th>번호</th>
                <td>{{ selectedEquipment.equipmentId }}</td>
              </tr>
              <tr>
                <th>위치</th>
                <td>{{ selectedEquipment.intersectionName ?? '-' }}</td>
              </tr>
              <tr>
                <th>모터전류</th>
                <td>{{ selectedEquipment.motorCurrent != null ? selectedEquipment.motorCurrent.toFixed(2) + ' A' : '-' }}</td>
              </tr>
              <tr>
                <th>베어링진동</th>
                <td>{{ selectedEquipment.bearingVibration != null ? selectedEquipment.bearingVibration.toFixed(3) + ' mm/s' : '-' }}</td>
              </tr>
              <tr>
                <th>온도</th>
                <td>{{ selectedEquipment.temperature != null ? selectedEquipment.temperature.toFixed(1) + ' °C' : '-' }}</td>
              </tr>
              <tr>
                <th>위험도</th>
                <td>
                  <span class="risk-dot-wrap">
                    <span class="risk-dot" :style="{ background: getRiskColor(selectedEquipment.riskLevel) }"></span>
                    <span :style="{ color: getRiskColor(selectedEquipment.riskLevel), fontWeight: 600 }">
                      {{ getRiskLabel(selectedEquipment.riskLevel) }}
                    </span>
                  </span>
                </td>
              </tr>
              <tr>
                <th>상태</th>
                <td>
                  <span class="status-badge" :style="getStatusStyle(selectedEquipment.status)">
                    {{ selectedEquipment.status }}
                  </span>
                </td>
              </tr>
              <tr>
                <th>잔여수명</th>
                <td :style="{ color: getRiskColor(selectedEquipment.riskLevel), fontWeight: 600 }">
                  {{ formatRul(selectedEquipment.rul) }}
                </td>
              </tr>
              <tr>
                <th>최근점검일</th>
                <td>{{ selectedEquipment.lastInspectionDate ?? '-' }}</td>
              </tr>
            </tbody>
          </table>

          <!-- 액션 버튼 -->
          <div class="detail-actions">
            <button class="btn-record" @click="onRecordCheck">기록확인</button>
            <button class="btn-alert" @click="onSendAlert">알림발송</button>
          </div>
        </div>
      </Transition>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import api from '../api'

const items = ref([])
const loading = ref(false)
const selectedEquipment = ref(null)
const currentPage = ref(1)
const totalPages = ref(1)

const filters = reactive({
  equipment: '',
  riskLevel: '',
  status: ''
})

const riskColors = {
  LOW: '#10B981',
  MEDIUM: '#FB923C',
  HIGH: '#F59E0B',
  CRITICAL: '#EF4444'
}

const riskLabels = {
  LOW: '정상',
  MEDIUM: '주의',
  HIGH: '경고',
  CRITICAL: '위험'
}

const statusColors = {
  '정상가동': '#10B981',
  '통신오류': '#3B82F6',
  '점검중': '#F59E0B',
  '점검요망': '#EF4444'
}

const getRiskColor = (riskLevel) => riskColors[riskLevel] ?? '#9CA3AF'
const getRiskLabel = (riskLevel) => riskLabels[riskLevel] ?? '-'

const getRiskBannerBg = (riskLevel) => {
  const color = getRiskColor(riskLevel)
  // 투명한 배너 배경색 (hex + 18 = 약 9% 투명도)
  return color + '18'
}

const getStatusStyle = (status) => {
  const color = statusColors[status] ?? '#9CA3AF'
  return {
    background: color,
    color: '#fff'
  }
}

const formatRul = (rul) => {
  if (rul == null) return '-'
  if (rul > 300) return '300일 이상'
  if (rul <= 3) return `${rul}일 이내`
  return `약 ${rul}일`
}

const pageNumbers = computed(() => {
  const pages = []
  const start = Math.max(1, currentPage.value - 2)
  const end = Math.min(totalPages.value, currentPage.value + 2)
  for (let i = start; i <= end; i++) pages.push(i)
  return pages
})

const fetchEquipments = async () => {
  loading.value = true
  try {
    const params = {}
    if (filters.equipment) params.equipment = filters.equipment
    if (filters.riskLevel) params.riskLevel = filters.riskLevel
    if (filters.status) params.status = filters.status
    params.page = currentPage.value
    params.size = 20

    const { data } = await api.get('/predictive/equipments', { params })
    if (data.success) {
      items.value = data.data.equipments
      totalPages.value = data.data.pagination.totalPages
    }
  } catch {
    items.value = []
  } finally {
    loading.value = false
  }
}

const search = () => {
  currentPage.value = 1
  selectedEquipment.value = null
  fetchEquipments()
}

const reset = () => {
  filters.equipment = ''
  filters.riskLevel = ''
  filters.status = ''
  currentPage.value = 1
  selectedEquipment.value = null
  fetchEquipments()
}

const changePage = (p) => {
  currentPage.value = p
  fetchEquipments()
}

const selectEquipment = async (item) => {
  try {
    const { data } = await api.get(`/predictive/equipments/${item.equipmentId}`)
    if (data.success) {
      selectedEquipment.value = data.data
    }
  } catch {
    selectedEquipment.value = item
  }
}

const onRecordCheck = () => {
  // 추후 구현
}

const onSendAlert = () => {
  // 추후 구현
}

onMounted(() => {
  fetchEquipments()
})
</script>

<style scoped>
.predictive {
  padding: 24px;
  max-width: 1400px;
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', sans-serif;
  background: #FFFFFF;
  min-height: 100%;
}

/* 섹션 헤더 */
.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.section-title {
  font-size: 16px;
  font-weight: 700;
  color: #1A1A2E;
  margin: 0;
}

.btn-refresh {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  background: #1A6DCC;
  color: #fff;
  border: none;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
}

.btn-refresh:hover {
  background: #1457A8;
  transform: translateY(-1px);
}

/* 필터 패널 */
.filter-panel {
  background: #fff;
  border-radius: 16px;
  padding: 18px 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06), 0 4px 16px rgba(0, 0, 0, 0.10), 0 8px 24px rgba(0, 0, 0, 0.05);
  margin-bottom: 18px;
  border: 1px solid rgba(226, 232, 240, 0.6);
}

.filter-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.filter-item {
  flex: 1;
  min-width: 150px;
}

.filter-item select {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid #E2E8F0;
  border-radius: 10px;
  font-size: 13px;
  color: #1A1A2E;
  background: #fff;
  outline: none;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
  box-sizing: border-box;
  font-family: inherit;
}

.filter-item select:focus {
  border-color: #1A6DCC;
  box-shadow: 0 0 0 3px rgba(26, 109, 204, 0.12);
}

.filter-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-shrink: 0;
}

.btn-search {
  padding: 10px 24px;
  background: #1A6DCC;
  color: #fff;
  border: none;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
  letter-spacing: 0.3px;
}

.btn-search:hover {
  background: #1457A8;
  transform: translateY(-1px);
}

.btn-reset {
  padding: 10px 18px;
  background: #E5E7EB;
  color: #4B5563;
  border: none;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
}

.btn-reset:hover {
  background: #D1D5DB;
}

/* 콘텐츠 영역 */
.content-area {
  display: flex;
  gap: 16px;
}

.list-section {
  flex: 1;
  min-width: 0;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06), 0 4px 16px rgba(0, 0, 0, 0.10), 0 8px 24px rgba(0, 0, 0, 0.05);
  overflow: hidden;
  border: 1px solid rgba(226, 232, 240, 0.6);
}

/* 테이블 */
.table-wrap {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

thead tr {
  background: #1A1A2E;
}

th {
  padding: 13px 16px;
  text-align: left;
  font-size: 13px;
  font-weight: 600;
  color: #FFFFFF;
}

td {
  padding: 12px 16px;
  font-size: 13px;
  color: #1A1A2E;
  border-bottom: 1px solid #F1F5FB;
}

tbody tr {
  cursor: pointer;
  transition: background 0.15s ease;
}

tbody tr:hover {
  background: rgba(26, 109, 204, 0.04);
}

tbody tr.selected {
  background: rgba(26, 109, 204, 0.08);
  border-left: 3px solid #1A6DCC;
}

.equipment-info-cell {
  padding-top: 10px;
  padding-bottom: 10px;
}

.equipment-name {
  font-weight: 600;
  color: #1A1A2E;
  font-size: 13px;
}

.equipment-location {
  font-size: 12px;
  color: #6B7280;
  margin-top: 2px;
}

.loading-cell,
.empty-cell {
  text-align: center;
  color: #9CA3AF;
  padding: 40px;
}

/* 위험도 */
.risk-dot-wrap {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.risk-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

/* 상태 배지 */
.status-badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}

/* 페이지네이션 */
.pagination {
  display: flex;
  justify-content: center;
  gap: 4px;
  padding: 14px;
}

.pagination button {
  width: 32px;
  height: 32px;
  border: 1px solid #E2E8F0;
  background: #fff;
  color: #4B5563;
  border-radius: 8px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s ease;
  font-family: inherit;
}

.pagination button:hover:not(:disabled) {
  background: rgba(26, 109, 204, 0.04);
  border-color: #1A6DCC;
  color: #1A6DCC;
}

.pagination button.active {
  background: #1A6DCC;
  color: #fff;
  border-color: #1A6DCC;
}

.pagination button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* 상세 패널 */
.detail-section {
  width: 360px;
  flex-shrink: 0;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06), 0 4px 16px rgba(0, 0, 0, 0.10), 0 8px 24px rgba(0, 0, 0, 0.05);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  align-self: flex-start;
  border: 1px solid rgba(226, 232, 240, 0.6);
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 12px;
  border-bottom: 1px solid #E2E8F0;
}

.detail-title {
  font-size: 15px;
  font-weight: 700;
  color: #1A1A2E;
}

.btn-close {
  width: 28px;
  height: 28px;
  border: none;
  background: #F1F5FB;
  border-radius: 50%;
  cursor: pointer;
  font-size: 13px;
  color: #6B7280;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s ease;
}

.btn-close:hover {
  background: #E2E8F0;
}

/* 위험도 배너 */
.risk-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border-radius: 12px;
  border: 1px solid;
}

.risk-banner-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  flex-shrink: 0;
}

.risk-banner-label {
  font-size: 14px;
  font-weight: 700;
}

.risk-banner-rul {
  margin-left: auto;
  font-size: 13px;
  color: #6B7280;
  font-weight: 500;
}

/* 상세 테이블 */
.detail-table {
  width: 100%;
  border-collapse: collapse;
}

.detail-table th {
  width: 80px;
  padding: 9px 10px;
  font-size: 12px;
  font-weight: 600;
  color: #6B7280;
  text-align: left;
  border-bottom: 1px solid #F1F5FB;
  white-space: nowrap;
}

.detail-table td {
  padding: 9px 10px;
  font-size: 13px;
  color: #1A1A2E;
  border-bottom: 1px solid #F1F5FB;
}

/* 액션 버튼 */
.detail-actions {
  display: flex;
  gap: 8px;
  padding-top: 4px;
}

.btn-record {
  flex: 1;
  padding: 11px;
  background: #1A6DCC;
  color: #fff;
  border: none;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
}

.btn-record:hover {
  background: #1457A8;
  transform: translateY(-1px);
}

.btn-alert {
  flex: 1;
  padding: 11px;
  background: #EF4444;
  color: #fff;
  border: none;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
}

.btn-alert:hover {
  background: #DC2626;
  transform: translateY(-1px);
}

/* 슬라이드 트랜지션 */
.slide-in-enter-active {
  transition: all 0.25s ease;
}

.slide-in-leave-active {
  transition: all 0.2s ease;
}

.slide-in-enter-from {
  opacity: 0;
  transform: translateX(20px);
}

.slide-in-leave-to {
  opacity: 0;
  transform: translateX(20px);
}

@media (max-width: 900px) {
  .content-area {
    flex-direction: column;
  }
  .detail-section {
    width: 100%;
  }
}
</style>
