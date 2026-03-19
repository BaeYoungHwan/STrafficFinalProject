<template>
  <div class="enforcement">
    <h1 class="page-title">단속 내역</h1>

    <!-- 필터 패널 -->
    <div class="filter-panel">
      <div class="filter-row">
        <div class="filter-item">
          <label>차량번호</label>
          <input
            v-model="filters.plateNumber"
            type="text"
            placeholder="차량번호 입력"
            @keyup.enter="search"
          />
        </div>
        <div class="filter-item">
          <label>위반유형</label>
          <select v-model="filters.violationType">
            <option value="">전체</option>
            <option value="과속">과속</option>
            <option value="신호위반">신호위반</option>
            <option value="중앙선 침범">중앙선 침범</option>
            <option value="차선 위반">차선 위반</option>
          </select>
        </div>
        <div class="filter-item">
          <label>상태</label>
          <select v-model="filters.status">
            <option value="">전체</option>
            <option value="대기중">대기중</option>
            <option value="승인">승인</option>
            <option value="반려">반려</option>
          </select>
        </div>
        <div class="filter-actions">
          <button class="btn-search" @click="search">조회</button>
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
                <td class="location-cell">{{ item.location }}</td>
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
          <button class="btn-close" @click="selectedItem = null">✕</button>
        </div>

        <!-- 차량 이미지 -->
        <div class="image-wrap">
          <img
            v-if="selectedItem.imageUrl"
            :src="selectedItem.imageUrl"
            alt="차량 이미지"
          />
          <div v-else class="no-image">이미지 없음</div>
        </div>

        <!-- 상세 정보 테이블 -->
        <table class="detail-table">
          <tr>
            <th>번호</th>
            <td>{{ selectedItem.violationId }}</td>
          </tr>
          <tr>
            <th>차량번호</th>
            <td>{{ selectedItem.plateNumber }}</td>
          </tr>
          <tr>
            <th>위반유형</th>
            <td>{{ selectedItem.violationType }}</td>
          </tr>
          <tr v-if="selectedItem.speedKmh">
            <th>속도</th>
            <td>{{ selectedItem.speedKmh }} km/h</td>
          </tr>
          <tr>
            <th>위치</th>
            <td>{{ selectedItem.location }}</td>
          </tr>
          <tr>
            <th>상태</th>
            <td>
              <span class="badge" :class="statusClass(selectedItem)">{{ statusLabel(selectedItem) }}</span>
            </td>
          </tr>
          <tr>
            <th>등록시간</th>
            <td>{{ selectedItem.detectedAt }}</td>
          </tr>
        </table>

        <!-- 액션 버튼 -->
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
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import api from '../api'

const items = ref([])
const loading = ref(false)
const submitting = ref(false)
const selectedItem = ref(null)

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
  return 'badge-yellow'
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

onMounted(fetchList)
</script>

<style scoped>
.enforcement {
  padding: 24px;
  max-width: 1400px;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  color: #1F3864;
  margin: 0 0 20px 0;
}

/* 필터 패널 */
.filter-panel {
  background: #fff;
  border-radius: 10px;
  padding: 18px 20px;
  box-shadow: 0 2px 10px rgba(30, 56, 100, 0.06);
  margin-bottom: 18px;
}

.filter-row {
  display: flex;
  align-items: flex-end;
  gap: 16px;
  flex-wrap: wrap;
}

.filter-item {
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-width: 160px;
}

.filter-item label {
  font-size: 12px;
  font-weight: 600;
  color: #6B7280;
}

.filter-item input,
.filter-item select {
  padding: 8px 12px;
  border: 1px solid #E2E8F0;
  border-radius: 6px;
  font-size: 13px;
  color: #1A1A2E;
  background: #fafbfd;
  outline: none;
  transition: border-color 0.2s;
}

.filter-item input:focus,
.filter-item select:focus {
  border-color: #1A6DCC;
  background: #fff;
}

.filter-actions {
  display: flex;
  gap: 8px;
  align-items: flex-end;
  padding-bottom: 1px;
}

.btn-search {
  padding: 8px 20px;
  background: #1A6DCC;
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-search:hover {
  background: #1457A8;
}

.btn-reset {
  padding: 8px 16px;
  background: #f0f0f0;
  color: #555;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-reset:hover {
  background: #e0e0e0;
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
  border-radius: 10px;
  box-shadow: 0 2px 10px rgba(30, 56, 100, 0.06);
  overflow: hidden;
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
  background: #F1F5FB;
}

th {
  padding: 12px 14px;
  text-align: left;
  font-size: 12px;
  font-weight: 700;
  color: #6B7280;
  border-bottom: 1px solid #E2E8F0;
}

td {
  padding: 12px 14px;
  font-size: 13px;
  color: #1A1A2E;
  border-bottom: 1px solid #F1F5FB;
}

tbody tr {
  cursor: pointer;
  transition: background 0.15s;
}

tbody tr:hover {
  background: #F8FAFD;
}

tbody tr.selected {
  background: #EBF3FF;
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
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 700;
}

.badge-green {
  background: #D1FAE5;
  color: #059669;
}

.badge-red {
  background: #FEE2E2;
  color: #DC2626;
}

.badge-yellow {
  background: #FEF3C7;
  color: #D97706;
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
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;
}

.pagination button:hover:not(:disabled) {
  background: #F1F5FB;
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
  width: 320px;
  flex-shrink: 0;
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 2px 10px rgba(30, 56, 100, 0.06);
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  align-self: flex-start;
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 10px;
  border-bottom: 1px solid #E2E8F0;
}

.detail-title {
  font-size: 14px;
  font-weight: 700;
  color: #1F3864;
}

.btn-close {
  width: 26px;
  height: 26px;
  border: none;
  background: #F1F5FB;
  border-radius: 50%;
  cursor: pointer;
  font-size: 13px;
  color: #6B7280;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-close:hover {
  background: #E2E8F0;
}

/* 이미지 */
.image-wrap {
  width: 100%;
  height: 160px;
  background: #F1F5FB;
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.image-wrap img {
  width: 100%;
  height: 100%;
  object-fit: cover;
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
  width: 70px;
  padding: 8px 10px;
  font-size: 12px;
  font-weight: 600;
  color: #6B7280;
  text-align: left;
  border-bottom: 1px solid #F1F5FB;
}

.detail-table td {
  padding: 8px 10px;
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
  padding: 10px;
  background: #10B981;
  color: #fff;
  border: none;
  border-radius: 7px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-approve:hover:not(:disabled) {
  background: #059669;
}

.btn-reject {
  flex: 1;
  padding: 10px;
  background: #EF4444;
  color: #fff;
  border: none;
  border-radius: 7px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-reject:hover:not(:disabled) {
  background: #DC2626;
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

@media (max-width: 900px) {
  .content-area {
    flex-direction: column;
  }
  .detail-section {
    width: 100%;
  }
}
</style>
