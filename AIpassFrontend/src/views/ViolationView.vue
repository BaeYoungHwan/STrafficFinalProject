<template>
  <section class="violation-page">
    <div class="page-header">
      <div>
        <h2>단속 내역 관리</h2>
        <p>위반 차량 조회, 승인/반려, 보정 완료 처리를 할 수 있습니다.</p>
      </div>
      <button class="refresh-btn" @click="searchViolations">새로고침</button>
    </div>

    <div class="search-panel">
      <input
        v-model="searchPlateNumber"
        type="text"
        class="search-input"
        placeholder="차량번호 검색"
        @keyup.enter="searchViolations"
      />

      <input
        v-model="searchViolationType"
        type="text"
        class="search-input"
        placeholder="위반유형 검색"
        @keyup.enter="searchViolations"
      />

      <input
        v-model="searchIntersectionName"
        type="text"
        class="search-input"
        placeholder="교차로명 검색"
        @keyup.enter="searchViolations"
      />

      <select v-model="searchFineStatus" class="search-select">
        <option value="ALL">전체 상태</option>
        <option value="UNPROCESSED">미처리</option>
        <option value="APPROVED">승인</option>
        <option value="REJECTED">반려</option>
      </select>

      <button class="search-btn" @click="searchViolations">검색</button>
      <button class="reset-btn" @click="resetSearch">초기화</button>
    </div>

    <div class="content-grid">
      <div class="list-panel">
        <table class="violation-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>차량번호</th>
              <th>위반유형</th>
              <th>교차로</th>
              <th>상태</th>
              <th>보정여부</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="item in violations"
              :key="item.violationId"
              :class="{ selected: selectedViolation && selectedViolation.violationId === item.violationId }"
              @click="selectViolation(item)"
            >
              <td>{{ item.violationId }}</td>
              <td>{{ item.plateNumber || '-' }}</td>
              <td>{{ item.violationType }}</td>
              <td>{{ item.intersectionName }}</td>
              <td>
                <span class="status-badge" :class="statusClass(item.fineStatus)">
                  {{ statusText(item.fineStatus) }}
                </span>
              </td>
              <td>
                <span class="corrected-badge" :class="item.isCorrected ? 'yes' : 'no'">
                  {{ item.isCorrected ? '수정됨' : '미수정' }}
                </span>
              </td>
            </tr>

            <tr v-if="violations.length === 0">
              <td colspan="6" class="empty-row">조회된 단속 내역이 없습니다.</td>
            </tr>
          </tbody>
        </table>

        <div class="pagination-row">
          <button class="page-btn" :disabled="page === 1" @click="goPrevPage">이전</button>
          <span class="page-info">{{ page }} / {{ totalPages || 1 }}</span>
          <button class="page-btn" :disabled="page >= totalPages" @click="goNextPage">다음</button>
        </div>
      </div>

      <div class="detail-panel">
        <template v-if="selectedViolation">
          <h3>상세 정보</h3>

          <div class="detail-item">
            <span class="label">번호</span>
            <span class="value">{{ selectedViolation.violationId }}</span>
          </div>

          <div class="detail-item">
            <span class="label">차량번호</span>
            <span class="value">{{ selectedViolation.plateNumber || '-' }}</span>
          </div>

          <div class="detail-item">
            <span class="label">위반유형</span>
            <span class="value">{{ selectedViolation.violationType }}</span>
          </div>

          <div class="detail-item">
            <span class="label">교차로</span>
            <span class="value">{{ selectedViolation.intersectionName }}</span>
          </div>

          <div class="detail-item">
            <span class="label">적발시각</span>
            <span class="value">{{ selectedViolation.detectedAt }}</span>
          </div>

          <div class="detail-item">
            <span class="label">처리상태</span>
            <span class="value">
              <span class="status-badge" :class="statusClass(selectedViolation.fineStatus)">
                {{ statusText(selectedViolation.fineStatus) }}
              </span>
            </span>
          </div>

          <div class="detail-item">
            <span class="label">보정여부</span>
            <span class="value">
              <span class="corrected-badge" :class="selectedViolation.isCorrected ? 'yes' : 'no'">
                {{ selectedViolation.isCorrected ? '수정됨' : '미수정' }}
              </span>
            </span>
          </div>

          <div class="detail-item">
            <span class="label">이미지</span>
            <span class="value">
              <template v-if="selectedViolation.imageUrl">
                <a :href="selectedViolation.imageUrl" target="_blank">
                  {{ selectedViolation.imageUrl }}
                </a>
              </template>
              <template v-else>
                이미지 없음
              </template>
            </span>
          </div>

          <div class="action-row" v-if="selectedViolation.fineStatus === 'UNPROCESSED'">
            <button class="approve-btn" @click="approveViolation">승인</button>
            <button class="reject-btn" @click="rejectViolation">반려</button>
          </div>

          <div class="action-row" v-if="!selectedViolation.isCorrected">
            <button class="correct-btn" @click="markCorrected">보정 완료 처리</button>
          </div>
        </template>

        <template v-else>
          <div class="empty-detail">목록에서 단속 내역을 선택하세요.</div>
        </template>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const violations = ref([])
const selectedViolation = ref(null)

const page = ref(1)
const size = ref(5)
const total = ref(0)

const searchPlateNumber = ref('')
const searchViolationType = ref('')
const searchIntersectionName = ref('')
const searchFineStatus = ref('ALL')

const totalPages = computed(() => Math.ceil(total.value / size.value))

const fetchViolations = async () => {
  try {
    const params = new URLSearchParams()
    params.append('page', page.value)
    params.append('size', size.value)

    if (searchPlateNumber.value) {
      params.append('plateNumber', searchPlateNumber.value)
    }

    if (searchViolationType.value) {
      params.append('violationType', searchViolationType.value)
    }

    if (searchIntersectionName.value) {
      params.append('intersectionName', searchIntersectionName.value)
    }

    if (searchFineStatus.value && searchFineStatus.value !== 'ALL') {
      params.append('fineStatus', searchFineStatus.value)
    }

    const response = await fetch(`http://localhost:9000/violations?${params.toString()}`)
    if (!response.ok) {
      alert('단속 내역 조회 실패')
      return
    }

    const result = await response.json()
    violations.value = result.data
    total.value = result.total

    if (violations.value.length > 0) {
      selectedViolation.value = violations.value[0]
    } else {
      selectedViolation.value = null
    }
  } catch (error) {
    console.error(error)
    alert('서버 연결 실패')
  }
}

const fetchViolationDetail = async (violationId) => {
  try {
    const response = await fetch(`http://localhost:9000/violations/${violationId}`)
    if (!response.ok) {
      alert('상세 조회 실패')
      return
    }

    selectedViolation.value = await response.json()
  } catch (error) {
    console.error(error)
    alert('서버 연결 실패')
  }
}

const selectViolation = async (item) => {
  await fetchViolationDetail(item.violationId)
}

const approveViolation = async () => {
  if (!selectedViolation.value) return

  try {
    const response = await fetch(
      `http://localhost:9000/violations/${selectedViolation.value.violationId}/approve`,
      { method: 'PATCH' }
    )

    if (!response.ok) {
      alert('승인 실패')
      return
    }

    const result = await response.json()
    if (result === true) {
      alert('승인 처리 완료')
      await fetchViolations()
      await fetchViolationDetail(selectedViolation.value.violationId)
    }
  } catch (error) {
    console.error(error)
    alert('서버 연결 실패')
  }
}

const rejectViolation = async () => {
  if (!selectedViolation.value) return

  try {
    const response = await fetch(
      `http://localhost:9000/violations/${selectedViolation.value.violationId}/reject`,
      { method: 'PATCH' }
    )

    if (!response.ok) {
      alert('반려 실패')
      return
    }

    const result = await response.json()
    if (result === true) {
      alert('반려 처리 완료')
      await fetchViolations()
      await fetchViolationDetail(selectedViolation.value.violationId)
    }
  } catch (error) {
    console.error(error)
    alert('서버 연결 실패')
  }
}

const markCorrected = async () => {
  if (!selectedViolation.value) return

  try {
    const response = await fetch(
      `http://localhost:9000/violations/${selectedViolation.value.violationId}/correct`,
      { method: 'PATCH' }
    )

    if (!response.ok) {
      alert('보정 완료 처리 실패')
      return
    }

    const result = await response.json()
    if (result === true) {
      alert('보정 완료 처리됨')
      await fetchViolations()
      await fetchViolationDetail(selectedViolation.value.violationId)
    }
  } catch (error) {
    console.error(error)
    alert('서버 연결 실패')
  }
}

const searchViolations = async () => {
  page.value = 1
  await fetchViolations()
}

const resetSearch = async () => {
  searchPlateNumber.value = ''
  searchViolationType.value = ''
  searchIntersectionName.value = ''
  searchFineStatus.value = 'ALL'
  page.value = 1
  await fetchViolations()
}

const goPrevPage = async () => {
  if (page.value > 1) {
    page.value--
    await fetchViolations()
  }
}

const goNextPage = async () => {
  if (page.value < totalPages.value) {
    page.value++
    await fetchViolations()
  }
}

const statusText = (status) => {
  if (status === 'UNPROCESSED') return '미처리'
  if (status === 'APPROVED') return '승인'
  if (status === 'REJECTED') return '반려'
  return status
}

const statusClass = (status) => {
  if (status === 'UNPROCESSED') return 'unprocessed'
  if (status === 'APPROVED') return 'approved'
  if (status === 'REJECTED') return 'rejected'
  return ''
}

onMounted(() => {
  fetchViolations()
})
</script>

<style scoped>
.violation-page {
  width: 100%;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 16px;
}

.page-header h2 {
  margin: 0 0 8px;
  font-size: 26px;
}

.page-header p {
  margin: 0;
  color: #666;
}

.refresh-btn {
  height: 42px;
  padding: 0 16px;
  border: none;
  border-radius: 12px;
  background: #1389ff;
  color: white;
  font-weight: 600;
  cursor: pointer;
}

.search-panel {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr 180px 120px 120px;
  gap: 10px;
  margin-bottom: 16px;
}

.search-input,
.search-select {
  height: 42px;
  border: none;
  border-radius: 12px;
  padding: 0 14px;
  background: white;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.06);
  outline: none;
}

.search-btn,
.reset-btn {
  height: 42px;
  border: none;
  border-radius: 12px;
  font-weight: 700;
  cursor: pointer;
}

.search-btn {
  background: #1e88e5;
  color: white;
}

.reset-btn {
  background: #dcdcdc;
  color: #111;
}

.content-grid {
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: 18px;
}

.list-panel,
.detail-panel {
  background: #f4f4f4;
  border-radius: 20px;
  padding: 16px;
  box-shadow: 0 8px 18px rgba(0, 0, 0, 0.06);
}

.violation-table {
  width: 100%;
  border-collapse: collapse;
  background: white;
  border-radius: 14px;
  overflow: hidden;
}

.violation-table thead {
  background: #1f2832;
  color: white;
}

.violation-table th,
.violation-table td {
  padding: 12px 10px;
  text-align: center;
  font-size: 14px;
  border-bottom: 1px solid #ececec;
}

.violation-table tbody tr {
  cursor: pointer;
  transition: background 0.15s ease;
}

.violation-table tbody tr:hover {
  background: #f8fbff;
}

.violation-table tbody tr.selected {
  background: #eef6ff;
}

.empty-row {
  text-align: center;
  color: #777;
}

.pagination-row {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 14px;
  margin-top: 14px;
}

.page-btn {
  min-width: 80px;
  height: 38px;
  border: none;
  border-radius: 10px;
  background: white;
  cursor: pointer;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.08);
}

.page-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.page-info {
  font-weight: 700;
}

.detail-panel h3 {
  margin: 0 0 16px;
  font-size: 22px;
}

.detail-item {
  display: flex;
  gap: 14px;
  padding: 10px 0;
  border-bottom: 1px solid #e5e5e5;
}

.label {
  width: 90px;
  font-weight: 700;
  color: #333;
}

.value {
  flex: 1;
  color: #555;
  word-break: break-word;
}

.status-badge,
.corrected-badge {
  display: inline-block;
  min-width: 70px;
  padding: 5px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  text-align: center;
}

.status-badge.unprocessed {
  background: #fff4d6;
  color: #a06b00;
}

.status-badge.approved {
  background: #e5f8eb;
  color: #1d7a3e;
}

.status-badge.rejected {
  background: #ffe6e6;
  color: #b42318;
}

.corrected-badge.yes {
  background: #e8f5e9;
  color: #2e7d32;
}

.corrected-badge.no {
  background: #f5f5f5;
  color: #666;
}

.action-row {
  display: flex;
  gap: 12px;
  margin-top: 18px;
}

.approve-btn,
.reject-btn,
.correct-btn {
  flex: 1;
  height: 44px;
  border: none;
  border-radius: 12px;
  color: white;
  font-weight: 700;
  cursor: pointer;
}

.approve-btn {
  background: #1e88e5;
}

.reject-btn {
  background: #d32f2f;
}

.correct-btn {
  background: #2e7d32;
}

.empty-detail {
  min-height: 260px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #777;
}

@media (max-width: 1200px) {
  .search-panel {
    grid-template-columns: 1fr 1fr;
  }

  .content-grid {
    grid-template-columns: 1fr;
  }
}
</style>