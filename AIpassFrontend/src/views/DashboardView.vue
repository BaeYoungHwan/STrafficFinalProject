<template>
  <div class="dashboard-page">
    <!-- 페이지 헤더 -->
    <div class="page-header">
      <h2 class="page-title">실시간 구간별 혼잡도 모니터링</h2>
    </div>

    <!-- 지도 섹션 -->
    <div class="map-card">
      <div ref="mapContainer" class="map-container"></div>
    </div>

    <!-- 위젯 그리드 -->
    <div class="widget-grid">

      <!-- 위젯 1: 누적 교통량 (미완성) -->
      <div class="widget widget-pending" @click="router.push('/statistics')">
        <div class="widget-header">
          <div class="widget-icon-wrap icon-blue">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
            </svg>
          </div>
          <span class="widget-title">누적 교통량</span>
        </div>
        <div class="widget-body pending-body">
          <div class="pending-graph">
            <svg width="100%" height="60" viewBox="0 0 200 60" preserveAspectRatio="none">
              <polyline points="0,50 40,35 80,40 120,20 160,28 200,15" fill="none" stroke="#CBD5E1" stroke-width="2" stroke-dasharray="4 3"/>
            </svg>
          </div>
          <p class="pending-text">데이터 준비 중</p>
        </div>
        <div class="widget-footer">
          <button class="widget-link-btn" @click.stop="router.push('/statistics')">
            통계 화면 보기
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
          </button>
        </div>
      </div>

      <!-- 위젯 2: 전체 CCTV 현황 (미완성) -->
      <div class="widget widget-pending" @click="router.push('/predictive')">
        <div class="widget-header">
          <div class="widget-icon-wrap icon-purple">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>
            </svg>
          </div>
          <span class="widget-title">전체 CCTV 현황</span>
        </div>
        <div class="widget-body pending-body">
          <div class="cctv-status-placeholder">
            <div class="status-row">
              <span class="status-dot dot-gray"></span><span class="status-label">정상 운영</span><span class="status-val">--</span>
            </div>
            <div class="status-row">
              <span class="status-dot dot-gray"></span><span class="status-label">점검 중</span><span class="status-val">--</span>
            </div>
            <div class="status-row">
              <span class="status-dot dot-gray"></span><span class="status-label">통신 오류</span><span class="status-val">--</span>
            </div>
          </div>
          <p class="pending-text">데이터 준비 중</p>
        </div>
        <div class="widget-footer">
          <button class="widget-link-btn" @click.stop="router.push('/predictive')">
            설비예지보전 보기
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
          </button>
        </div>
      </div>

      <!-- 위젯 3: 오늘 단속 건수 -->
      <div class="widget widget-enforcement" @click="router.push('/enforcement')">
        <div class="widget-header">
          <div class="widget-icon-wrap icon-red">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
          </div>
          <span class="widget-title">오늘 단속 건수</span>
        </div>
        <div class="widget-body enforcement-body">
          <template v-if="violationLoading">
            <div class="skeleton-count"></div>
            <div class="skeleton-sub"></div>
          </template>
          <template v-else>
            <div class="enforcement-count">
              <span class="count-number">{{ violation.totalCount ?? '--' }}</span>
              <span class="count-unit">건</span>
            </div>
            <div class="enforcement-sub">
              <div class="sub-item">
                <span class="sub-label">과속</span>
                <span class="sub-val speed">{{ violation.speedCount ?? '--' }}</span>
              </div>
              <div class="sub-divider"></div>
              <div class="sub-item">
                <span class="sub-label">기타</span>
                <span class="sub-val other">{{ violation.otherCount ?? '--' }}</span>
              </div>
            </div>
          </template>
        </div>
        <div class="widget-footer">
          <button class="widget-link-btn" @click.stop="router.push('/enforcement')">
            단속 내역 보기
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
          </button>
        </div>
      </div>

      <!-- 위젯 4: 날씨 -->
      <div class="widget widget-weather" @click="openWeather">
        <div class="widget-header">
          <div class="widget-icon-wrap icon-sky">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
            </svg>
          </div>
          <span class="widget-title">날씨</span>
        </div>
        <div class="widget-body weather-body">
          <template v-if="weatherLoading">
            <div class="skeleton-weather"></div>
          </template>
          <template v-else>
            <div class="weather-main">
              <img
                v-if="weatherIconPath"
                :src="weatherIconPath"
                :alt="weather.skyCondition || '날씨'"
                class="weather-icon"
                @error="weatherIconError = true"
              />
              <div v-else class="weather-icon-placeholder">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#94A3B8" stroke-width="1.5"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/></svg>
              </div>
              <div class="weather-temp">
                <span class="temp-value">{{ weather.temperature != null ? weather.temperature : '--' }}</span>
                <span class="temp-unit">°C</span>
              </div>
            </div>
            <div class="weather-location">인천광역시 강화군</div>
            <div class="weather-details">
              <span class="detail-item">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z"/></svg>
                습도 {{ weather.humidity != null ? weather.humidity + '%' : '--' }}
              </span>
              <span class="detail-sep">|</span>
              <span class="detail-item">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9.59 4.59A2 2 0 1 1 11 8H2m10.59 11.41A2 2 0 1 0 14 16H2m15.73-8.27A2.5 2.5 0 1 1 19.5 12H2"/></svg>
                남서 {{ weather.windSpeed != null ? weather.windSpeed + 'm/s' : '--' }}
              </span>
            </div>
          </template>
        </div>
        <div class="widget-footer">
          <button class="widget-link-btn" @click.stop="openWeather">
            날씨 상세 보기
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
          </button>
        </div>
      </div>

    </div>

    <!-- CCTV 스트림 모달 -->
    <Teleport to="body">
      <div v-if="streamModal.open" class="modal-backdrop" @click.self="closeModal">
        <div class="modal-box">
          <div class="modal-header">
            <div class="modal-title-wrap">
              <span class="live-badge">LIVE</span>
              <span class="modal-name">{{ streamModal.name }}</span>
            </div>
            <button class="modal-close" @click="closeModal">&#x2715;</button>
          </div>
          <div class="modal-stream">
            <template v-if="streamModal.loading">
              <div class="stream-loading">스트림 로딩 중...</div>
            </template>
            <template v-else-if="streamModal.error || !streamModal.url">
              <div class="stream-error">스트림을 불러올 수 없습니다.</div>
            </template>
            <template v-else>
              <img
                :src="streamModal.url"
                class="stream-img"
                alt="CCTV 스트림"
                @error="streamModal.error = true"
              />
            </template>
          </div>
        </div>
      </div>
    </Teleport>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import api from '../api'

// ─── Leaflet 기본 마커 경로 오류 방지 ─────────────────────────────────────────
delete L.Icon.Default.prototype._getIconUrl

const router = useRouter()

// ─── 지도 ─────────────────────────────────────────────────────────────────────
const mapContainer = ref(null)
let map = null

// ─── 교차로 데이터 ────────────────────────────────────────────────────────────
const intersections = ref([])

// ─── 단속 건수 ────────────────────────────────────────────────────────────────
const violation = ref({})
const violationLoading = ref(true)

// ─── 날씨 ─────────────────────────────────────────────────────────────────────
const weather = ref({})
const weatherLoading = ref(true)
const weatherIconError = ref(false)

// ─── 스트림 모달 ──────────────────────────────────────────────────────────────
const streamModal = ref({
  open: false,
  name: '',
  url: '',
  loading: false,
  error: false
})

// ─── 날씨 아이콘 경로 계산 ────────────────────────────────────────────────────
const weatherIconPath = computed(() => {
  if (!weather.value || weatherIconError.value) return ''
  const sky = weather.value.skyCondition || ''
  const hour = new Date().getHours()
  const prefix = (hour >= 6 && hour < 18) ? '낮' : '밤'

  let suffix = '바람'
  if (/맑음|화창/.test(sky)) suffix = '화창'
  else if (/구름많음|흐림/.test(sky)) suffix = '구름'
  else if (/비|소나기/.test(sky)) suffix = '비'
  else if (/눈/.test(sky)) suffix = '눈'

  return `/icons/${prefix}_${suffix}.png`
})

// ─── 지도 초기화 ──────────────────────────────────────────────────────────────
const initMap = () => {
  if (!mapContainer.value) return

  map = L.map(mapContainer.value, {
    zoomControl: true,
    scrollWheelZoom: false
  })

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    maxZoom: 19
  }).addTo(map)

  map.fitBounds([[37.720, 126.350], [37.790, 126.530]])
}

// ─── CCTV 마커 추가 ───────────────────────────────────────────────────────────
const addMarkers = () => {
  if (!map || intersections.value.length === 0) return

  const cctvIcon = L.icon({
    iconUrl: '/icons/CCTV.png',
    iconSize: [32, 32],
    iconAnchor: [16, 32],
    popupAnchor: [0, -34]
  })

  intersections.value.forEach(intersection => {
    if (!intersection.latitude || !intersection.longitude) return

    const marker = L.marker(
      [intersection.latitude, intersection.longitude],
      { icon: cctvIcon }
    ).addTo(map)

    // 호버 팝업
    marker.bindPopup(`<strong>${intersection.name}</strong>`, {
      closeButton: false,
      offset: [0, -28]
    })

    marker.on('mouseover', () => marker.openPopup())
    marker.on('mouseout', () => marker.closePopup())

    // 클릭 시 스트림 모달
    marker.on('click', () => openModal(intersection))
  })
}

// ─── 모달 열기 ────────────────────────────────────────────────────────────────
const openModal = async (intersection) => {
  streamModal.value = {
    open: true,
    name: intersection.name || 'CCTV',
    url: '',
    loading: true,
    error: false
  }

  try {
    const res = await api.get('/cctv/ai-target')
    const data = res.data?.data || res.data
    const url = data?.streamUrl || data?.stream_url || ''
    streamModal.value.url = url
    streamModal.value.error = !url
  } catch {
    streamModal.value.error = true
  } finally {
    streamModal.value.loading = false
  }
}

// ─── 모달 닫기 ────────────────────────────────────────────────────────────────
const closeModal = () => {
  streamModal.value.open = false
  streamModal.value.url = ''
  streamModal.value.error = false
}

// ─── 키보드 이벤트 ────────────────────────────────────────────────────────────
const onKeydown = (e) => {
  if (e.key === 'Escape') closeModal()
}

// ─── API: 교차로 목록 ─────────────────────────────────────────────────────────
const fetchIntersections = async () => {
  try {
    const res = await api.get('/dashboard/intersections')
    intersections.value = res.data?.data || res.data || []
    await nextTick()
    addMarkers()
  } catch {
    intersections.value = []
  }
}

// ─── API: 오늘 단속 건수 ──────────────────────────────────────────────────────
const fetchViolations = async () => {
  violationLoading.value = true
  try {
    const res = await api.get('/dashboard/today-violations')
    violation.value = res.data?.data || res.data || {}
  } catch {
    violation.value = {}
  } finally {
    violationLoading.value = false
  }
}

// ─── API: 날씨 ────────────────────────────────────────────────────────────────
const fetchWeather = async () => {
  weatherLoading.value = true
  try {
    const res = await api.get('/dashboard/weather')
    weather.value = res.data?.data || res.data || {}
  } catch {
    weather.value = {}
  } finally {
    weatherLoading.value = false
  }
}

// ─── 날씨 링크 ────────────────────────────────────────────────────────────────
const openWeather = () => {
  window.open('https://weather.naver.com/map/09110615', '_blank')
}

// ─── 생명주기 ─────────────────────────────────────────────────────────────────
onMounted(async () => {
  await nextTick()
  initMap()
  document.addEventListener('keydown', onKeydown)

  await Promise.all([
    fetchIntersections(),
    fetchViolations(),
    fetchWeather()
  ])
})

onUnmounted(() => {
  if (map) {
    map.remove()
    map = null
  }
  document.removeEventListener('keydown', onKeydown)
})
</script>

<style scoped>
.dashboard-page {
  padding: 28px 32px;
  background: #F4F6FA;
  min-height: 100%;
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', sans-serif;
}

/* ─── 헤더 ──────────────────────────────────────────────────────────────────── */
.page-header {
  margin-bottom: 20px;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  color: #1A1A2E;
  margin: 0;
}

/* ─── 지도 카드 ─────────────────────────────────────────────────────────────── */
.map-card {
  background: #fff;
  border-radius: 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  overflow: hidden;
  margin-bottom: 20px;
}

.map-container {
  width: 100%;
  height: 450px;
}

/* ─── 위젯 그리드 ───────────────────────────────────────────────────────────── */
.widget-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

/* ─── 공통 위젯 ─────────────────────────────────────────────────────────────── */
.widget {
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  display: flex;
  flex-direction: column;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  overflow: hidden;
}

.widget:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}

.widget-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 18px 12px;
  border-bottom: 1px solid #F1F5F9;
}

.widget-icon-wrap {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.icon-blue   { background: #E8F1FB; color: #1A6DCC; }
.icon-purple { background: #EDE9FE; color: #7C3AED; }
.icon-red    { background: #FEE2E2; color: #EF4444; }
.icon-sky    { background: #E0F2FE; color: #0284C7; }

.widget-title {
  font-size: 14px;
  font-weight: 700;
  color: #1A1A2E;
}

.widget-body {
  flex: 1;
  padding: 16px 18px;
}

.widget-footer {
  padding: 10px 18px 14px;
  border-top: 1px solid #F1F5F9;
}

.widget-link-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  background: none;
  border: none;
  color: #1A6DCC;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  padding: 0;
  font-family: inherit;
  transition: color 0.2s;
}

.widget-link-btn:hover {
  color: #1457A8;
}

/* ─── 미완성 위젯 공통 ──────────────────────────────────────────────────────── */
.widget-pending {
  background: #FAFBFC;
}

.pending-body {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.pending-graph {
  width: 100%;
  opacity: 0.4;
}

.pending-text {
  font-size: 13px;
  color: #94A3B8;
  margin: 0;
  font-weight: 500;
}

/* ─── CCTV 현황 플레이스홀더 ────────────────────────────────────────────────── */
.cctv-status-placeholder {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 6px;
}

.status-row {
  display: flex;
  align-items: center;
  gap: 8px;
  opacity: 0.35;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.dot-gray { background: #CBD5E1; }

.status-label {
  flex: 1;
  font-size: 12px;
  color: #64748B;
}

.status-val {
  font-size: 13px;
  font-weight: 700;
  color: #1A1A2E;
}

/* ─── 단속 위젯 ─────────────────────────────────────────────────────────────── */
.enforcement-body {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.enforcement-count {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.count-number {
  font-size: 48px;
  font-weight: 800;
  color: #1A1A2E;
  line-height: 1;
}

.count-unit {
  font-size: 18px;
  font-weight: 600;
  color: #6B7280;
}

.enforcement-sub {
  display: flex;
  align-items: center;
  gap: 16px;
  width: 100%;
  justify-content: center;
}

.sub-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.sub-label {
  font-size: 12px;
  color: #94A3B8;
  font-weight: 500;
}

.sub-val {
  font-size: 20px;
  font-weight: 700;
}

.sub-val.speed { color: #EF4444; }
.sub-val.other { color: #F59E0B; }

.sub-divider {
  width: 1px;
  height: 32px;
  background: #E2E8F0;
}

/* ─── 날씨 위젯 ─────────────────────────────────────────────────────────────── */
.weather-body {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.weather-main {
  display: flex;
  align-items: center;
  gap: 12px;
}

.weather-icon {
  width: 64px;
  height: 64px;
  object-fit: contain;
  flex-shrink: 0;
}

.weather-icon-placeholder {
  width: 64px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.weather-temp {
  display: flex;
  align-items: baseline;
  gap: 2px;
}

.temp-value {
  font-size: 42px;
  font-weight: 800;
  color: #1A1A2E;
  line-height: 1;
}

.temp-unit {
  font-size: 18px;
  font-weight: 600;
  color: #6B7280;
}

.weather-location {
  font-size: 13px;
  color: #64748B;
  font-weight: 500;
}

.weather-details {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: center;
}

.detail-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #64748B;
}

.detail-sep {
  color: #CBD5E1;
  font-size: 12px;
}

/* ─── 스켈레톤 ──────────────────────────────────────────────────────────────── */
.skeleton-count {
  width: 80px;
  height: 56px;
  border-radius: 8px;
  background: linear-gradient(90deg, #e0e7ef 25%, #f0f4fa 50%, #e0e7ef 75%);
  background-size: 200% 100%;
  animation: shimmer 1.4s infinite;
}

.skeleton-sub {
  width: 120px;
  height: 24px;
  border-radius: 6px;
  background: linear-gradient(90deg, #e0e7ef 25%, #f0f4fa 50%, #e0e7ef 75%);
  background-size: 200% 100%;
  animation: shimmer 1.4s infinite;
}

.skeleton-weather {
  width: 100%;
  height: 80px;
  border-radius: 8px;
  background: linear-gradient(90deg, #e0e7ef 25%, #f0f4fa 50%, #e0e7ef 75%);
  background-size: 200% 100%;
  animation: shimmer 1.4s infinite;
}

@keyframes shimmer {
  0%   { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* ─── 모달 ──────────────────────────────────────────────────────────────────── */
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.75);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.modal-box {
  background: #0d0d1a;
  border-radius: 20px;
  overflow: hidden;
  width: 72vw;
  max-width: 1100px;
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.6);
  border: 1.5px solid rgba(26, 109, 204, 0.4);
  animation: modalIn 0.2s ease;
}

@keyframes modalIn {
  from { transform: scale(0.92); opacity: 0; }
  to   { transform: scale(1);    opacity: 1; }
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  background: rgba(255, 255, 255, 0.04);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.modal-title-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
}

.live-badge {
  background: rgba(239, 68, 68, 0.88);
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: 6px;
  letter-spacing: 0.5px;
}

.modal-name {
  font-size: 15px;
  font-weight: 700;
  color: #fff;
}

.modal-close {
  background: rgba(255, 255, 255, 0.1);
  border: none;
  color: #fff;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  font-size: 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
}

.modal-close:hover {
  background: rgba(239, 68, 68, 0.7);
}

.modal-stream {
  width: 100%;
  aspect-ratio: 16 / 9;
  background: #000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stream-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.stream-loading,
.stream-error {
  color: rgba(255, 255, 255, 0.6);
  font-size: 14px;
  text-align: center;
}

.stream-error {
  color: rgba(239, 68, 68, 0.8);
}

/* ─── 반응형 ────────────────────────────────────────────────────────────────── */
@media (max-width: 1200px) {
  .widget-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .dashboard-page {
    padding: 16px;
  }
  .widget-grid {
    grid-template-columns: 1fr;
  }
  .map-container {
    height: 300px;
  }
  .modal-box {
    width: 95vw;
  }
}
</style>
