<template>
  <div class="enforcement">
    <!-- 위반 차량 상세 정보 조회 -->
    <div class="section-header">
      <h2 class="section-title">* 위반 차량 상세 정보 조회</h2>
      <div class="section-actions">
        <div class="stream-btn-group">
          <button class="btn-cctv btn-cctv-speed" @click="openSpeedStream" title="실시간 과속 감지 모니터">
            <span class="btn-cctv-label">과속</span>
            <img src="/icons/CCTV.png" alt="CCTV" class="cctv-icon" />
          </button>
          <button class="btn-cctv btn-cctv-line" @click="openLineStream" title="실시간 실선침범 감지 모니터">
            <span class="btn-cctv-label">실선</span>
            <img src="/icons/CCTV.png" alt="CCTV" class="cctv-icon cctv-icon-orange" />
          </button>
        </div>
        <button class="btn-refresh" @click="fetchList" title="새로 고침">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/>
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
          </svg>
          새로 고침
        </button>
      </div>
    </div>

    <!-- 필터 패널 -->
    <div class="filter-panel">
      <div class="filter-row">
        <div class="filter-item">
          <input
            v-model="filters.plateNumber"
            type="text"
            placeholder="차량번호 검색"
            @keyup.enter="search"
          />
        </div>
        <div class="filter-item">
          <select v-model="filters.violationType">
            <option value="">위반 유형 검색</option>
            <option value="과속">과속</option>
            <option value="신호위반">신호위반</option>
            <option value="중앙선 침범">중앙선 침범</option>
            <option value="실선 침범">실선 침범</option>
          </select>
        </div>
        <div class="filter-item">
          <select v-model="filters.status">
            <option value="">상태 필터</option>
            <option value="대기중">대기중</option>
            <option value="승인">승인</option>
            <option value="반려">반려</option>
          </select>
        </div>
        <div class="filter-actions">
          <button class="btn-search" @click="search">검 색</button>
          <button class="btn-reset" @click="reset">초기화</button>
        </div>
      </div>
    </div>

    <!-- 콘텐츠 영역 -->
    <div class="content-area" :class="{ 'has-detail': selectedItem }">
      <!-- 목록 -->
      <div class="list-section">
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>No.</th>
                <th>차량번호</th>
                <th>위반유형</th>
                <th>위치</th>
                <th>상태</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="loading">
                <td colspan="5" class="loading-cell">불러오는 중...</td>
              </tr>
              <tr v-else-if="items.length === 0">
                <td colspan="5" class="empty-cell">단속 내역이 없습니다.</td>
              </tr>
              <tr
                v-for="(item, index) in items"
                :key="item.violationId"
                :class="{ selected: selectedItem && selectedItem.violationId === item.violationId }"
                @click="selectItem(item)"
              >
                <td>{{ (page - 1) * size + index + 1 }}</td>
                <td>{{ item.plateNumber }}</td>
                <td>{{ item.violationType }}</td>
                <td class="location-cell">강화대교</td>
                <td>
                  <span class="badge" :class="statusClass(item)">{{ statusLabel(item) }}</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- 페이지네이션 -->
        <div class="pagination" v-if="totalPages > 1">
          <button :disabled="page === 1" @click="changePage(page - 1)">&lt;</button>
          <button
            v-for="p in pageNumbers"
            :key="p"
            :class="{ active: p === page }"
            @click="changePage(p)"
          >{{ p }}</button>
          <button :disabled="page === totalPages" @click="changePage(page + 1)">&gt;</button>
        </div>
      </div>

      <!-- 상세 패널 -->
      <div class="detail-section" v-if="selectedItem">
        <div class="detail-header">
          <span class="detail-title">상세 정보</span>
          <div class="detail-header-actions">
            <button v-if="!editMode" class="btn-edit" @click="startEdit">수정</button>
            <button v-else class="btn-cancel-edit" @click="editMode = false">취소</button>
            <button class="btn-close" @click="selectedItem = null; editMode = false">✕</button>
          </div>
        </div>

        <!-- 차량 이미지: 전체(16:9) → 번호판 크롭(5:1) 상하 스택 -->
        <div class="images-stack">
          <div class="image-main-wrap">
            <div class="image-box-label">차량 전체</div>
            <img
              v-if="selectedItem.srcImageUrl"
              :src="'/ai/images/' + selectedItem.srcImageUrl"
              alt="차량 전체 사진"
              @error="$event.target.style.display='none'"
            />
            <div v-else class="no-image">이미지 없음</div>
          </div>
          <div class="image-plate-wrap">
            <div class="image-box-label">번호판 크롭</div>
            <img
              v-if="selectedItem.imageUrl"
              :src="'/ai/images/' + selectedItem.imageUrl"
              alt="번호판"
              @error="$event.target.style.display='none'"
            />
            <div v-else class="no-image">이미지 없음</div>
          </div>
        </div>


        <!-- 상세 정보 테이블 -->
        <table class="detail-table">
          <tbody>
            <tr>
              <th>번호</th>
              <td>{{ selectedItem.violationId }}</td>
            </tr>
            <tr>
              <th>차량번호</th>
              <td>
                <template v-if="!editMode">{{ selectedItem.plateNumber }}</template>
                <input v-else v-model="editForm.plateNumber" class="edit-input" />
              </td>
            </tr>
            <tr>
              <th>위반유형</th>
              <td>
                <template v-if="!editMode">{{ selectedItem.violationType }}</template>
                <select v-else v-model="editForm.violationType" class="edit-select">
                  <option>과속</option>
                  <option>신호위반</option>
                  <option>중앙선 침범</option>
                  <option>실선 침범</option>
                </select>
              </td>
            </tr>
            <tr v-if="selectedItem.speedKmh">
              <th>속도</th>
              <td>{{ selectedItem.speedKmh }} km/h</td>
            </tr>
            <tr>
              <th>위치</th>
              <td>강화대교</td>
            </tr>
            <tr>
              <th>상태</th>
              <td>
                <template v-if="!editMode">
                  <span class="badge" :class="statusClass(selectedItem)">{{ statusLabel(selectedItem) }}</span>
                </template>
                <select v-else v-model="editForm.fineStatus" class="edit-select">
                  <option>대기중</option>
                  <option>승인</option>
                  <option>반려</option>
                </select>
              </td>
            </tr>
            <tr>
              <th>등록시간</th>
              <td>{{ selectedItem.detectedAt }}</td>
            </tr>
          </tbody>
        </table>

        <!-- 완료 안내 문구 -->
        <div v-if="editSuccess" class="edit-success-msg">✓ 수정이 완료되었습니다.</div>

        <!-- 수정 모드 업데이트 버튼 -->
        <div class="detail-actions" v-if="editMode">
          <button class="btn-update" :disabled="submitting" @click="updateViolation">
            {{ submitting ? '저장 중...' : '업데이트' }}
          </button>
        </div>

        <!-- 기존 승인/반려 버튼 -->
        <template v-else>
          <div class="detail-actions" v-if="selectedItem.fineStatus === 'UNPROCESSED' || !selectedItem.fineStatus">
            <button class="btn-approve" :disabled="submitting" @click="updateStatus('승인')">
              {{ submitting ? '처리 중...' : '승인' }}
            </button>
            <button class="btn-reject" :disabled="submitting" @click="updateStatus('반려')">
              {{ submitting ? '처리 중...' : '반려' }}
            </button>
          </div>
          <div class="detail-actions" v-else>
            <p class="status-done">처리 완료 ({{ statusLabel(selectedItem) }})</p>
          </div>
        </template>
      </div>
    </div>
  </div>

  <!-- 실시간 스트리밍 모달 -->
  <div v-if="showStreamModal" class="stream-modal-overlay" @click.self="showStreamModal = false">
    <div class="stream-modal">
      <div class="stream-modal-header">
        <span>{{ streamTitle }}</span>
        <button class="btn-close" @click="showStreamModal = false">✕</button>
      </div>
      <img
        :src="streamUrl"
        class="stream-img"
        :alt="streamTitle"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import api from '../api'
import { useNotificationStore } from '../stores/notification'

const notifStore = useNotificationStore()
watch(() => notifStore.violationTick, () => fetchList())

const items = ref([])
const loading = ref(false)
const submitting = ref(false)
const selectedItem = ref(null)

// 수정 모드
const editMode = ref(false)
const editForm = reactive({ plateNumber: '', violationType: '', fineStatus: '' })
const editSuccess = ref(false)

// 스트리밍 모달
const showStreamModal = ref(false)
watch(showStreamModal, (val) => {
  const scrollbarWidth = window.innerWidth - document.documentElement.clientWidth
  document.body.style.overflow = val ? 'hidden' : ''
  document.body.style.paddingRight = val ? scrollbarWidth + 'px' : ''
})
const streamUrl = ref('')
const streamTitle = ref('실시간 과속 감지 모니터')

function openSpeedStream() {
  streamTitle.value = '실시간 과속 감지 모니터'
  const base = import.meta.env.DEV
    ? (import.meta.env.VITE_FASTAPI_SPEED_URL || 'http://localhost:8000') + '/api/v1/stream/video'
    : '/ai/api/v1/stream/video'
  streamUrl.value = base + '?t=' + Date.now()
  showStreamModal.value = true
}

function openLineStream() {
  streamTitle.value = '실시간 실선침범 감지 모니터'
  const base = import.meta.env.DEV
    ? (import.meta.env.VITE_FASTAPI_LINE_URL || 'http://localhost:8001') + '/api/v1/stream/video'
    : '/ai-line/api/v1/stream/video'
  streamUrl.value = base + '?t=' + Date.now()
  showStreamModal.value = true
}

const page = ref(1)
const size = ref(10)
const total = ref(0)
const totalPages = ref(0)

const filters = reactive({
  plateNumber: '',
  violationType: '',
  status: ''
})

const pageNumbers = computed(() => {
  const pages = []
  const start = Math.max(1, page.value - 2)
  const end = Math.min(totalPages.value, page.value + 2)
  for (let i = start; i <= end; i++) pages.push(i)
  return pages
})

const statusClass = (item) => {
  const s = item.fineStatus || item.status
  if (s === 'APPROVED' || s === '승인') return 'badge-green'
  if (s === 'REJECTED' || s === '반려') return 'badge-red'
  return 'badge-gray'
}

const statusLabel = (item) => {
  const s = item.fineStatus || ''
  if (s === 'APPROVED') return '승인'
  if (s === 'REJECTED') return '반려'
  return '대기중'
}

const fetchList = async () => {
  loading.value = true
  try {
    const params = { page: page.value, size: size.value }
    if (filters.plateNumber) params.plateNumber = filters.plateNumber
    if (filters.violationType) params.violationType = filters.violationType
    if (filters.status) params.status = filters.status

    const res = await api.get('/enforcement/violations', { params })
    const data = res.data.data
    items.value = data.items
    total.value = data.total
    totalPages.value = data.totalPages
  } catch (e) {
    items.value = []
  } finally {
    loading.value = false
  }
}

const search = () => {
  page.value = 1
  selectedItem.value = null
  fetchList()
}

const reset = () => {
  filters.plateNumber = ''
  filters.violationType = ''
  filters.status = ''
  page.value = 1
  selectedItem.value = null
  fetchList()
}

const changePage = (p) => {
  page.value = p
  fetchList()
}

const selectItem = (item) => {
  selectedItem.value = item
  editMode.value = false
  editSuccess.value = false
}

const startEdit = () => {
  const s = selectedItem.value
  editForm.plateNumber = s.plateNumber
  editForm.violationType = s.violationType
  editForm.fineStatus = statusLabel(s)  // '대기중' / '승인' / '반려'
  editMode.value = true
}

const updateViolation = async () => {
  submitting.value = true
  try {
    await api.put(`/enforcement/violations/${selectedItem.value.violationId}`, {
      plateNumber: editForm.plateNumber,
      violationType: editForm.violationType,
      status: editForm.fineStatus
    })
    const statusMap = { '승인': 'APPROVED', '반려': 'REJECTED', '대기중': 'UNPROCESSED' }
    selectedItem.value.plateNumber = editForm.plateNumber
    selectedItem.value.violationType = editForm.violationType
    selectedItem.value.fineStatus = statusMap[editForm.fineStatus] ?? 'UNPROCESSED'
    const idx = items.value.findIndex(i => i.violationId === selectedItem.value.violationId)
    if (idx !== -1) Object.assign(items.value[idx], selectedItem.value)
    editMode.value = false
    editSuccess.value = true
    setTimeout(() => { editSuccess.value = false }, 3000)
  } catch (e) {
    alert(`수정에 실패했습니다. (${e.response?.status ?? e.message ?? 'unknown'})`)
  } finally {
    submitting.value = false
  }
}

const updateStatus = async (newStatus) => {
  submitting.value = true
  try {
    await api.put(`/enforcement/violations/${selectedItem.value.violationId}/status`, { status: newStatus })
    selectedItem.value.status = newStatus
    selectedItem.value.fineStatus = newStatus === '승인' ? 'APPROVED' : 'REJECTED'
    const idx = items.value.findIndex(i => i.violationId === selectedItem.value.violationId)
    if (idx !== -1) items.value[idx].fineStatus = selectedItem.value.fineStatus
  } catch (e) {
    alert('상태 변경에 실패했습니다.')
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  fetchList()
})
</script>

<style scoped>
.enforcement {
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
}

.btn-refresh:hover {
  background: #1457A8;
  transform: translateY(-1px);
}

.section-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.stream-btn-group {
  display: flex;
  align-items: center;
  gap: 6px;
}

.btn-cctv {
  background: none;
  border: 1px solid #2a2a4a;
  border-radius: 6px;
  padding: 4px 8px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  transition: border-color 0.2s, background 0.2s;
}

.btn-cctv:hover {
  background: rgba(26, 109, 204, 0.06);
}

.btn-cctv-line {
  border-color: #EA580C;
}

.btn-cctv-line:hover {
  background: rgba(234, 88, 12, 0.06);
}

.btn-cctv-label {
  font-size: 9px;
  font-weight: 700;
  color: #2a2a4a;
  line-height: 1;
}

.btn-cctv-line .btn-cctv-label {
  color: #EA580C;
}

.cctv-icon {
  width: 24px;
  height: 24px;
  object-fit: contain;
  pointer-events: none;
}

.cctv-icon-orange {
  filter: sepia(1) saturate(5) hue-rotate(-10deg) brightness(0.85);
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

.filter-item input,
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

.filter-item input::placeholder {
  color: #9CA3AF;
}

.filter-item input:focus,
.filter-item select:focus {
  border-color: #1A6DCC;
  box-shadow: 0 0 0 3px rgba(26, 109, 204, 0.12);
  background: #fff;
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
  border-radius: 12px 12px 0 0;
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
}

.location-cell {
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.loading-cell,
.empty-cell {
  text-align: center;
  color: #9CA3AF;
  padding: 40px;
}

/* 상태 뱃지 */
.badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
}

.badge-green {
  background: rgba(16, 185, 129, 0.12);
  color: #059669;
}

.badge-red {
  background: rgba(239, 68, 68, 0.12);
  color: #DC2626;
}

.badge-gray {
  background: rgba(107, 114, 128, 0.12);
  color: #4B5563;
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
  width: 380px;
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

/* 이미지 상하 스택 */
.images-stack {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* 차량 전체: 16:9 비율 */
.image-main-wrap {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  background: #F1F5FB;
  border-radius: 10px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 번호판 크롭: 5:1 비율 (실제 번호판 비율) */
.image-plate-wrap {
  position: relative;
  width: 100%;
  aspect-ratio: 5 / 1;
  background: #F1F5FB;
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.image-main-wrap img,
.image-plate-wrap img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.image-box-label {
  position: absolute;
  top: 4px;
  left: 6px;
  font-size: 10px;
  color: #6B7280;
  font-weight: 600;
  background: rgba(255, 255, 255, 0.85);
  padding: 1px 5px;
  border-radius: 4px;
  z-index: 1;
}

.no-image {
  font-size: 13px;
  color: #9CA3AF;
}

/* 상세 테이블 */
.detail-table {
  width: 100%;
  border-collapse: collapse;
}

.detail-table th {
  width: 72px;
  padding: 9px 10px;
  font-size: 12px;
  font-weight: 600;
  color: #6B7280;
  text-align: left;
  border-bottom: 1px solid #F1F5FB;
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

.btn-approve {
  flex: 1;
  padding: 11px;
  background: #10B981;
  color: #fff;
  border: none;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
}

.btn-approve:hover:not(:disabled) {
  background: #059669;
  transform: translateY(-1px);
}

.btn-reject {
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

.btn-reject:hover:not(:disabled) {
  background: #DC2626;
  transform: translateY(-1px);
}

.btn-approve:disabled,
.btn-reject:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.status-done {
  font-size: 13px;
  color: #6B7280;
  margin: 0;
  text-align: center;
  width: 100%;
}

/* 수정 모드 */
.detail-header-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.btn-edit {
  padding: 5px 12px;
  background: #1A6DCC;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
  font-family: inherit;
}

.btn-edit:hover {
  background: #1457A8;
}

.btn-cancel-edit {
  padding: 5px 12px;
  background: #E5E7EB;
  color: #4B5563;
  border: none;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  font-family: inherit;
}

.edit-input {
  width: 100%;
  padding: 5px 8px;
  border: 1px solid #1A6DCC;
  border-radius: 6px;
  font-size: 13px;
  color: #1A1A2E;
  outline: none;
  box-sizing: border-box;
  font-family: inherit;
}

.edit-select {
  width: 100%;
  padding: 5px 8px;
  border: 1px solid #1A6DCC;
  border-radius: 6px;
  font-size: 13px;
  color: #1A1A2E;
  background: #fff;
  outline: none;
  font-family: inherit;
}

.btn-update {
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

.btn-update:hover:not(:disabled) {
  background: #1457A8;
  transform: translateY(-1px);
}

.btn-update:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.edit-success-msg {
  background: rgba(16, 185, 129, 0.12);
  color: #059669;
  font-size: 13px;
  font-weight: 600;
  padding: 10px 14px;
  border-radius: 10px;
  text-align: center;
}

/* 스트리밍 모달 */
.stream-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.65);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.stream-modal {
  background: #1A1A2E;
  border-radius: 16px;
  overflow: hidden;
  width: 660px;
  max-width: 95vw;
}

.stream-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  color: #fff;
  font-size: 14px;
  font-weight: 600;
}

.stream-modal-header .btn-close {
  background: rgba(255,255,255,0.1);
  color: #fff;
}

.stream-modal-header .btn-close:hover {
  background: rgba(255,255,255,0.2);
}

.stream-img {
  display: block;
  width: 100%;
  height: 480px;
  border: none;
  background: #000;
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
