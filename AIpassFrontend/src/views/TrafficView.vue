<template>
  <section class="traffic-dashboard">
    <div class="dashboard-bg"></div>

    <div class="dashboard-topbar">
      <div class="topbar-left">{{ currentTimeText }}</div>
      <div class="topbar-title">스마트 교통 관제시스템: 통합 대시보드</div>
      <div class="topbar-right">
        <button class="mini-toggle-btn" @click="toggleMapPanel">
          {{ showMapPanel ? '지도데이터 닫기' : '지도데이터 열기' }}
        </button>
        <span>Admin</span>
      </div>
    </div>

    <!-- 좌상단 : 교통 인텔리전스 -->
    <div class="panel traffic-intel">
      <h3>교통 인텔리전스</h3>

      <div class="cctv-preview-grid">
        <div v-for="cam in cctvList" :key="cam.id" class="cctv-preview-card">
          <div class="cctv-preview-label">{{ cam.title }}</div>
          <div class="cctv-preview-image"></div>
          <div class="cctv-preview-footer">{{ cam.footer }}</div>
        </div>
      </div>

      <div class="traffic-density-row">
        <div class="density-info-box">
          <div class="density-title">Traffic Density</div>
          <div class="density-sub">({{ densityLabel }} {{ trafficStatus.signalPercent }}%)</div>
        </div>

        <div class="density-gauge-wrap">
          <div class="density-gauge">
            <div class="density-gauge-inner">
              <div class="density-text-main">{{ densityLabel }}</div>
              <div class="density-text-sub">{{ trafficStatus.signalPercent }}%</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 우상단 : 통계 및 리포트 -->
    <div class="panel report-panel">
      <h3>통계 및 리포트</h3>

      <div class="kpi-stack">
        <div class="kpi-box">
          <div class="kpi-label">오늘 누적 교통량</div>
          <div class="kpi-value">{{ dashboard.todayTrafficTotal }}</div>
        </div>
        <div class="kpi-box">
          <div class="kpi-label">미처리 위반</div>
          <div class="kpi-value">{{ dashboard.unprocessedCount }}</div>
        </div>
        <div class="kpi-box">
          <div class="kpi-label">위험 장비</div>
          <div class="kpi-value">{{ dashboard.riskEquipmentCount }}</div>
        </div>
      </div>

      <div class="mini-chart-box">
        <div class="mini-chart-title">주간 교통량 추이</div>
        <svg viewBox="0 0 220 90" class="mini-chart">
          <polyline
            fill="none"
            stroke="#5d9cec"
            stroke-width="3"
            :points="weeklyTrafficPolyline"
          />
        </svg>
      </div>

      <div class="mini-chart-box">
        <div class="mini-chart-title">일간 위반 건수 분석</div>
        <div class="bar-chart">
          <div
            v-for="(value, index) in violationBars"
            :key="index"
            class="bar-item"
          >
            <div class="bar" :style="{ height: value + '%' }"></div>
          </div>
        </div>
      </div>

      <div class="alert-list-box">
        <div class="alert-list-title">최근 알림</div>
        <div v-if="dashboard.recentAlerts.length === 0" class="empty-alert-text">
          최근 알림 없음
        </div>
        <div v-else class="alert-list">
          <div v-for="(alert, index) in dashboard.recentAlerts" :key="index" class="alert-item">
            {{ alert }}
          </div>
        </div>
      </div>

      <button class="report-btn">리포트 생성 및 다운로드</button>
    </div>

    <!-- 중앙 지도 영역 -->
    <div class="center-overlay">
      <template v-if="showMapView">
        <div class="signal-badge">
          {{ selectedMapPoint ? selectedMapPoint.intersectionName : '교차로 선택 대기중' }}
        </div>

        <div class="leaflet-map-wrap">
          <div ref="mapContainer" class="leaflet-map"></div>
        </div>

        <div class="pip-card">
          <div class="pip-title">PIP</div>
          <div class="pip-image"></div>
        </div>

        <div class="center-control-bar">
          <button title="선택 교차로 이동" @click="focusSelectedIntersection">📍</button>
          <button class="active" title="지도 새로고침" @click="loadMapData">맵</button>
          <button title="지도 닫기" @click="closeMapView">✖</button>
          <button title="긴급 경로 테스트" @click="testPriorityRoute">🚑</button>
        </div>

        <div v-if="routePathPoints.length > 0" class="route-debug-box">
          경로 포인트 수: {{ routePathPoints.length }} / 우선 제어 교차로:
          {{ routeInfo.priorityCount }}
        </div>
      </template>

      <template v-else>
        <div class="map-empty-state"></div>
      </template>
    </div>

    <!-- 좌하단 : 위반 단속 관리 -->
    <div class="panel violation-panel">
      <h3>위반 단속 관리</h3>
      <div class="table-subtitle">최근 데이터 테이블</div>

      <div class="violation-table-wrap">
        <table class="violation-table">
          <thead>
            <tr>
              <th>차량번호</th>
              <th>위반유형</th>
              <th>위치</th>
              <th>상태</th>
              <th>액션</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="pagedViolationRows.length === 0">
              <td colspan="5">데이터 없음</td>
            </tr>

            <tr v-for="item in pagedViolationRows" :key="item.id">
              <td>{{ item.plateNumber || '-' }}</td>
              <td>{{ item.violationType || '-' }}</td>
              <td>{{ item.location || '-' }}</td>
              <td>{{ item.status }}</td>
              <td class="action-cell">
                <button
                  v-if="item.status === '승인 대기'"
                  class="approve-btn"
                  @click="approveViolation(item)"
                >
                  승인
                </button>
                <button
                  v-if="item.status === '승인 대기'"
                  class="reject-btn"
                  @click="rejectViolation(item)"
                >
                  반려
                </button>
                <span v-if="item.status !== '승인 대기'">-</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="violation-pagination">
        <button
          class="page-btn"
          :disabled="violationCurrentPage === 1"
          @click="goViolationPage(violationCurrentPage - 1)"
        >
          이전
        </button>

        <div class="page-info">
          {{ violationCurrentPage }} / {{ violationTotalPages }}
        </div>

        <button
          class="page-btn"
          :disabled="violationCurrentPage === violationTotalPages"
          @click="goViolationPage(violationCurrentPage + 1)"
        >
          다음
        </button>
      </div>
    </div>

    <!-- 우하단 : 기기 라이프사이클 -->
    <div class="panel lifecycle-panel">
      <h3>기기 라이프사이클</h3>

      <div class="lifecycle-gauge-row">
        <div class="device-gauge-box">
          <div class="device-gauge"></div>
          <div class="device-label">
            PTZ Camera<br />
            {{ trafficStatus.cameraState || '정상' }}
          </div>
        </div>

        <div class="device-gauge-box">
          <div class="device-gauge warning"></div>
          <div class="device-label">
            Signal Controller<br />
            {{ trafficStatus.signalState || '주의' }}
          </div>
        </div>
      </div>

      <div class="device-alert-box">
        {{ lifecycleAlertText }}
      </div>

      <div class="maintenance-text">
        최근 정비: {{ trafficStatus.lastMaintenanceText || '정보 없음' }}
      </div>

      <button class="repair-btn">수리 기사 배정/호출</button>
    </div>

    <!-- 지도 데이터 확인 패널 -->
    <transition name="fade">
      <div v-if="showMapPanel" class="panel map-data-panel">
        <div class="map-panel-header">
          <h3>지도 데이터 확인</h3>
          <div class="map-panel-header-actions">
            <button class="reload-btn" @click="loadMapData">새로고침</button>
            <button class="close-panel-btn" @click="showMapPanel = false">닫기</button>
          </div>
        </div>

        <div class="map-panel-sub">/traffic/map-data 연동 확인</div>

        <div v-if="mapLoading" class="map-status">불러오는 중...</div>
        <div v-else-if="mapErrorMessage" class="map-status error">{{ mapErrorMessage }}</div>

        <div v-else class="map-list">
          <div
            v-for="point in mapPoints"
            :key="point.intersectionId"
            class="map-item"
            @click="selectMapPoint(point)"
          >
            <div class="map-item-title">
              {{ point.intersectionName }}
            </div>

            <div class="map-item-row">
              <span>ID</span>
              <strong>{{ point.intersectionId }}</strong>
            </div>

            <div class="map-item-row">
              <span>위도</span>
              <strong>{{ point.latitude }}</strong>
            </div>

            <div class="map-item-row">
              <span>경도</span>
              <strong>{{ point.longitude }}</strong>
            </div>

            <div class="map-item-row">
              <span>장비 수</span>
              <strong>{{ point.equipmentList?.length || 0 }}개</strong>
            </div>
          </div>
        </div>

        <div v-if="selectedMapPoint" class="selected-map-box">
          <div class="selected-title">선택된 교차로</div>
          <div class="selected-name">{{ selectedMapPoint.intersectionName }}</div>

          <div class="selected-equipment-title">장비 목록</div>

          <div
            v-if="selectedMapPoint.equipmentList && selectedMapPoint.equipmentList.length > 0"
            class="selected-equipment-list"
          >
            <div
              v-for="equipment in selectedMapPoint.equipmentList"
              :key="equipment.equipmentId"
              class="selected-equipment-item"
            >
              <span>#{{ equipment.equipmentId }} / {{ equipment.equipmentType }}</span>
              <strong>{{ equipment.status }}</strong>
            </div>
          </div>

          <div v-else class="no-equipment-text">
            연결된 장비 없음
          </div>

          <div class="selected-map-actions">
            <button
              class="priority-open-btn"
              @click="showMapView ? closeMapView() : openMapView()"
            >
              {{ showMapView ? '지도 닫기' : '지도 열기' }}
            </button>

            <button class="priority-open-btn danger" @click="testPriorityRoute">
              긴급 경로 보기
            </button>
          </div>
        </div>
      </div>
    </transition>

    <!-- 긴급 팝업 -->
    <transition name="fade">
      <div
        v-if="showEmergencyPopup"
        class="emergency-modal-backdrop"
        @click.self="closeEmergencyPopup"
      >
        <div class="emergency-modal">
          <button class="emergency-close-btn" @click="closeEmergencyPopup">✕</button>

          <h3>EMERGENCY PATHWAY CONTROL</h3>

          <div class="emergency-chip">1 Emergency</div>

          <div class="emergency-message">
            EMERGENCY VEHICLE DETECTED - PATH AUTO-MAPPED
          </div>

          <div class="emergency-location-text">
            출발: <strong>{{ routeInfo.start }}</strong><br />
            도착: <strong>{{ routeInfo.end }}</strong>
          </div>

          <button class="emergency-main-btn" @click="runEmergencyControl">
            ENABLE EMERGENCY PATH
          </button>

          <div class="emergency-eta">
            AMBULANCE ETA: <strong>{{ routeInfo.eta }}</strong>
          </div>

          <div class="emergency-bottom-alert">
            ▲ EMERGENCY VEHICLE DETECTED - PATH AUTO MAPPED
          </div>
        </div>
      </div>
    </transition>
  </section>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

const API_BASE = 'http://localhost:9000'

const trafficStatus = ref({
  temperature: 0,
  vibration: 0,
  riskScore: 0,
  signalPercent: 0,
  signalState: '',
  cameraPercent: 0,
  cameraState: '',
  operationStatus: '',
  failureRisk: '',
  lastMaintenanceText: '',
})

const dashboard = ref({
  todayTrafficTotal: 0,
  trafficChangeRate: 0,
  unprocessedCount: 0,
  riskEquipmentCount: 0,
  trafficTrend: [],
  recentAlerts: [],
})

const cctvList = ref([
  { id: 1, title: 'CCTV 강남', footer: 'Camera 1: Gangnam' },
  { id: 2, title: 'CCTV 서초', footer: 'Camera 2: Seocho' },
])

const routeInfo = ref({
  start: '',
  end: '',
  eta: '정보 없음',
  priorityCount: 0,
})

const violationRows = ref([])
const violationCurrentPage = ref(1)
const violationPageSize = 5

const pagedViolationRows = computed(() => {
  const start = (violationCurrentPage.value - 1) * violationPageSize
  const end = start + violationPageSize
  return violationRows.value.slice(start, end)
})

const violationTotalPages = computed(() => {
  return Math.max(1, Math.ceil(violationRows.value.length / violationPageSize))
})

const goViolationPage = (page) => {
  if (page < 1 || page > violationTotalPages.value) return
  violationCurrentPage.value = page
}

const mapPoints = ref([])
const mapLoading = ref(false)
const mapErrorMessage = ref('')
const selectedMapPoint = ref(null)

const showMapPanel = ref(false)
const showMapView = ref(false)
const showEmergencyPopup = ref(false)

const routePathPoints = ref([])
const currentTimeText = ref('')

const mapContainer = ref(null)

let leafletMap = null
let intersectionMarkers = []
let routePolyline = null
let emergencyVehicleMarker = null
let clockTimer = null

const updateClock = () => {
  const now = new Date()
  currentTimeText.value = now.toLocaleTimeString('ko-KR', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: true,
  })
}

const normalizeFineStatus = (fineStatus) => {
  if (fineStatus === 'APPROVED') return '승인 완료'
  if (fineStatus === 'REJECTED') return '반려'
  return '승인 대기'
}

const fetchTrafficStatus = async () => {
  try {
    const response = await fetch(`${API_BASE}/traffic/status`)
    if (!response.ok) throw new Error('traffic/status 조회 실패')
    const data = await response.json()

    trafficStatus.value = {
      ...trafficStatus.value,
      ...data,
    }
  } catch (error) {
    console.error('traffic/status 조회 실패:', error)
  }
}

const fetchDashboardSummary = async () => {
  try {
    const response = await fetch(`${API_BASE}/dashboard/summary`)
    if (!response.ok) throw new Error('dashboard/summary 조회 실패')
    const data = await response.json()

    dashboard.value = {
      ...dashboard.value,
      ...data,
      trafficTrend: Array.isArray(data.trafficTrend) ? data.trafficTrend : [],
      recentAlerts: Array.isArray(data.recentAlerts) ? data.recentAlerts : [],
    }
  } catch (error) {
    console.error('dashboard/summary 조회 실패:', error)
  }
}

const fetchViolations = async () => {
  try {
    const response = await fetch(`${API_BASE}/violations?page=1&size=50`)
    if (!response.ok) throw new Error('violations 조회 실패')

    const data = await response.json()
    const list = Array.isArray(data.data) ? data.data : []

    violationRows.value = list.map((item) => ({
      id: item.violationId,
      plateNumber: item.plateNumber,
      violationType: item.violationType,
      location: item.intersectionName,
      status: normalizeFineStatus(item.fineStatus),
      fineStatus: item.fineStatus,
      intersectionId: item.intersectionId,
      imageUrl: item.imageUrl,
      detectedAt: item.detectedAt,
      isCorrected: item.isCorrected,
    }))

    violationCurrentPage.value = 1
  } catch (error) {
    console.error('violations 조회 실패:', error)
  }
}

const createIntersectionIcon = () => {
  return L.divIcon({
    className: 'custom-intersection-marker',
    html: '<div class="intersection-marker-dot"></div>',
    iconSize: [16, 16],
    iconAnchor: [8, 8],
  })
}

const createEmergencyVehicleIcon = () => {
  return L.divIcon({
    className: 'custom-emergency-marker',
    html: '<div class="emergency-vehicle-marker">🚑</div>',
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  })
}

const initLeafletMap = () => {
  if (leafletMap || !mapContainer.value) return

  leafletMap = L.map(mapContainer.value, {
    zoomControl: true,
    attributionControl: true,
  })

  leafletMap.setView([37.500622, 127.036456], 13)

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors',
  }).addTo(leafletMap)

  setTimeout(() => {
    if (leafletMap) {
      leafletMap.invalidateSize(true)
    }
  }, 200)
}

const clearIntersectionMarkers = () => {
  if (!leafletMap) return

  intersectionMarkers.forEach((marker) => leafletMap.removeLayer(marker))
  intersectionMarkers = []
}

const renderIntersectionMarkers = () => {
  if (!leafletMap) return

  clearIntersectionMarkers()

  mapPoints.value.forEach((point) => {
    if (point.latitude == null || point.longitude == null) return

    const marker = L.marker([point.latitude, point.longitude], {
      icon: createIntersectionIcon(),
    }).addTo(leafletMap)

    marker.bindPopup(`
      <div style="font-size:12px;">
        <strong>${point.intersectionName}</strong><br/>
        ID: ${point.intersectionId}<br/>
        장비 수: ${point.equipmentList?.length || 0}개
      </div>
    `)

    marker.on('click', () => {
      selectMapPoint(point)
    })

    intersectionMarkers.push(marker)
  })
}

const drawRouteOnMap = (pathPoints) => {
  if (!leafletMap) return

  clearRoute()

  if (!pathPoints || pathPoints.length === 0) return

  const validPoints = pathPoints.filter(
    (point) => point.latitude != null && point.longitude != null
  )

  if (validPoints.length === 0) return

  const latLngs = validPoints.map((point) => [point.latitude, point.longitude])

  routePolyline = L.polyline(latLngs, {
    color: '#ff2e2e',
    weight: 6,
    opacity: 0.9,
  }).addTo(leafletMap)

  emergencyVehicleMarker = L.marker(latLngs[0], {
    icon: createEmergencyVehicleIcon(),
  }).addTo(leafletMap)

  leafletMap.fitBounds(routePolyline.getBounds(), { padding: [30, 30] })
}

const clearRoute = () => {
  routePathPoints.value = []

  if (leafletMap && routePolyline) {
    leafletMap.removeLayer(routePolyline)
    routePolyline = null
  }

  if (leafletMap && emergencyVehicleMarker) {
    leafletMap.removeLayer(emergencyVehicleMarker)
    emergencyVehicleMarker = null
  }
}

const syncSelectedMapPoint = () => {
  if (mapPoints.value.length === 0) {
    selectedMapPoint.value = null
    return
  }

  if (!selectedMapPoint.value?.intersectionId) {
    selectedMapPoint.value = mapPoints.value[0]
    return
  }

  const matched = mapPoints.value.find(
    (point) => point.intersectionId === selectedMapPoint.value.intersectionId
  )

  selectedMapPoint.value = matched || mapPoints.value[0]
}

const openMapView = async () => {
  showMapView.value = true

  await nextTick()

  if (!leafletMap) {
    initLeafletMap()
  }

  await loadMapData()

  await nextTick()

  setTimeout(() => {
    if (leafletMap) {
      leafletMap.invalidateSize(true)
      renderIntersectionMarkers()

      if (
        selectedMapPoint.value?.latitude != null &&
        selectedMapPoint.value?.longitude != null
      ) {
        leafletMap.setView(
          [selectedMapPoint.value.latitude, selectedMapPoint.value.longitude],
          15
        )
      } else if (mapPoints.value.length > 0) {
        const firstPoint = mapPoints.value[0]
        if (firstPoint.latitude != null && firstPoint.longitude != null) {
          leafletMap.setView([firstPoint.latitude, firstPoint.longitude], 13)
        }
      }
    }
  }, 300)
}

const closeMapView = () => {
  showMapView.value = false
  closeEmergencyPopup()
  clearRoute()
}

const focusSelectedIntersection = () => {
  if (!leafletMap || !selectedMapPoint.value) return
  if (selectedMapPoint.value.latitude == null || selectedMapPoint.value.longitude == null) return

  leafletMap.setView(
    [selectedMapPoint.value.latitude, selectedMapPoint.value.longitude],
    15
  )
}

const loadMapData = async () => {
  mapLoading.value = true
  mapErrorMessage.value = ''

  try {
    const response = await fetch(`${API_BASE}/traffic/map-data`)
    if (!response.ok) throw new Error('지도 데이터 조회 실패')

    const data = await response.json()
    mapPoints.value = Array.isArray(data) ? data : []

    syncSelectedMapPoint()

    if (leafletMap) {
      renderIntersectionMarkers()
    }
  } catch (error) {
    console.error('지도 데이터 조회 실패:', error)
    mapErrorMessage.value = '지도 데이터를 불러오지 못했습니다.'
  } finally {
    mapLoading.value = false
  }
}

const selectMapPoint = async (point) => {
  selectedMapPoint.value = point

  if (leafletMap && point?.latitude != null && point?.longitude != null) {
    leafletMap.setView([point.latitude, point.longitude], 15)
  }

  try {
    const response = await fetch(`${API_BASE}/traffic/intersection/${point.intersectionId}`)
    if (!response.ok) throw new Error('교차로 상세 조회 실패')

    const data = await response.json()

    routeInfo.value.start = data.intersectionName || point.intersectionName || ''
    trafficStatus.value.temperature = data.temperature ?? trafficStatus.value.temperature
    trafficStatus.value.vibration = data.vibration ?? trafficStatus.value.vibration
    trafficStatus.value.riskScore = data.riskScore ?? trafficStatus.value.riskScore
  } catch (error) {
    console.error('교차로 상세 조회 실패:', error)
  }
}

const toggleMapPanel = async () => {
  showMapPanel.value = !showMapPanel.value

  if (showMapPanel.value && mapPoints.value.length === 0) {
    await loadMapData()
  }
}

const openEmergencyPopup = () => {
  showEmergencyPopup.value = true
}

const closeEmergencyPopup = () => {
  showEmergencyPopup.value = false
}

const runEmergencyControl = async () => {
  if (!selectedMapPoint.value?.intersectionId) {
    alert('교차로를 먼저 선택하세요.')
    return
  }

  try {
    const response = await fetch(`${API_BASE}/traffic/control`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        intersectionId: selectedMapPoint.value.intersectionId,
        controlType: 'AUTO_EMERGENCY',
        controlReason: '긴급차량 감지로 인한 교차로 우선 신호 제어',
      }),
    })

    if (!response.ok) {
      alert('긴급 신호 제어 요청 실패')
      return
    }

    const result = await response.json()

    if (result === true) {
      alert('긴급 신호 제어가 등록되었습니다.')
      closeEmergencyPopup()
    } else {
      alert('긴급 신호 제어 등록 실패')
    }
  } catch (error) {
    console.error('긴급 신호 제어 실패:', error)
    alert('서버 연결 실패')
  }
}

const testPriorityRoute = async () => {
  if (!selectedMapPoint.value?.intersectionId) {
    alert('교차로를 먼저 선택하세요.')
    return
  }

  try {
    await openMapView()

    const startId = selectedMapPoint.value.intersectionId

    const otherPoint = mapPoints.value.find(
      (point) => point.intersectionId !== startId
    )

    if (!otherPoint?.intersectionId) {
      alert('도착 교차로를 찾을 수 없습니다.')
      return
    }

    const endId = otherPoint.intersectionId

    const response = await fetch(`${API_BASE}/traffic/priority-route`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        startIntersectionId: startId,
        endIntersectionId: endId,
        vehicleType: 'AMBULANCE',
      }),
    })

    if (!response.ok) {
      alert('우선 경로 조회 실패')
      return
    }

    const data = await response.json()

    routeInfo.value.start = data.startIntersectionName || routeInfo.value.start
    routeInfo.value.end = data.endIntersectionName || routeInfo.value.end
    routeInfo.value.eta = data.eta || '정보 없음'
    routeInfo.value.priorityCount = data.priorityCount || 0

    routePathPoints.value = Array.isArray(data.pathPoints) ? data.pathPoints : []

    drawRouteOnMap(routePathPoints.value)
    openEmergencyPopup()
  } catch (error) {
    console.error('우선 경로 API 호출 중 오류 발생:', error)
    alert('우선 경로 API 호출 중 오류 발생')
  }
console.log('showMapView:', showMapView.value)
console.log('mapContainer:', mapContainer.value)
console.log('mapPoints:', mapPoints.value)
console.log('selectedMapPoint:', selectedMapPoint.value)
console.log('leafletMap:', leafletMap)
}

const approveViolation = async (item) => {
  try {
    const response = await fetch(`${API_BASE}/violations/${item.id}/approve`, {
      method: 'PATCH',
    })

    if (!response.ok) {
      alert('승인 처리 실패')
      return
    }

    const result = await response.json()
    if (result === true) {
      await fetchViolations()
      await fetchDashboardSummary()
    } else {
      alert('승인 처리 실패')
    }
  } catch (error) {
    console.error('승인 처리 실패:', error)
    alert('서버 연결 실패')
  }
}

const rejectViolation = async (item) => {
  try {
    const response = await fetch(`${API_BASE}/violations/${item.id}/reject`, {
      method: 'PATCH',
    })

    if (!response.ok) {
      alert('반려 처리 실패')
      return
    }

    const result = await response.json()
    if (result === true) {
      await fetchViolations()
      await fetchDashboardSummary()
    } else {
      alert('반려 처리 실패')
    }
  } catch (error) {
    console.error('반려 처리 실패:', error)
    alert('서버 연결 실패')
  }
}

const densityLabel = computed(() => {
  const p = Number(trafficStatus.value.signalPercent || 0)
  if (p >= 80) return 'LOW'
  if (p >= 50) return 'MID'
  return 'HIGH'
})

const lifecycleAlertText = computed(() => {
  return trafficStatus.value.failureRisk === '높음'
    ? '고장 위험 임계치 초과'
    : trafficStatus.value.failureRisk
      ? `기기 상태: ${trafficStatus.value.failureRisk}`
      : '기기 상태 안정적'
})

const weeklyTrafficPolyline = computed(() => {
  const values =
    dashboard.value.trafficTrend && dashboard.value.trafficTrend.length > 0
      ? dashboard.value.trafficTrend
      : [0, 0, 0, 0, 0, 0, 0, 0]

  const max = Math.max(...values, 1)
  const width = 210
  const height = 70
  const startX = 5
  const step = width / Math.max(values.length - 1, 1)

  return values
    .map((value, index) => {
      const x = startX + step * index
      const y = 80 - (value / max) * height
      return `${x},${y}`
    })
    .join(' ')
})

const violationBars = computed(() => {
  const values =
    dashboard.value.trafficTrend && dashboard.value.trafficTrend.length > 0
      ? dashboard.value.trafficTrend
      : [0, 0, 0, 0, 0, 0, 0, 0]

  const max = Math.max(...values, 1)
  return values.map((value) => Math.max(8, Math.round((value / max) * 100)))
})

onMounted(async () => {
  updateClock()
  clockTimer = setInterval(updateClock, 1000)

  await fetchTrafficStatus()
  await fetchDashboardSummary()
  await fetchViolations()
  await loadMapData()
})

onUnmounted(() => {
  if (clockTimer) {
    clearInterval(clockTimer)
  }

  if (leafletMap) {
    leafletMap.remove()
    leafletMap = null
  }
})
</script>

<style scoped>
.traffic-dashboard {
  position: relative;
  min-height: 900px;
  height: 100vh;
  border-radius: 24px;
  overflow: hidden;
  padding: 12px;
  background: #eceff3;
}

.dashboard-bg {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(rgba(255, 255, 255, 0.34), rgba(255, 255, 255, 0.34)),
    url('../assets/login-bg.jpg');
  background-size: cover;
  background-position: center;
  filter: grayscale(8%);
}

.dashboard-topbar {
  position: relative;
  z-index: 20;
  height: 40px;
  background: rgba(255, 255, 255, 0.58);
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 14px;
  margin-bottom: 10px;
  font-weight: 700;
  font-size: 13px;
}

.topbar-title {
  font-size: 16px;
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.mini-toggle-btn {
  border: none;
  background: #1389ff;
  color: white;
  padding: 6px 10px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 700;
}

.panel {
  position: absolute;
  z-index: 15;
  background: rgba(255, 255, 255, 0.88);
  border-radius: 18px;
  box-shadow: 0 10px 22px rgba(0, 0, 0, 0.12);
  padding: 14px;
  backdrop-filter: blur(3px);
}

.panel h3 {
  margin: 0 0 10px;
  font-size: 15px;
}

.traffic-intel {
  left: 12px;
  top: 58px;
  width: 310px;
}

.cctv-preview-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.cctv-preview-card {
  background: rgba(0, 0, 0, 0.78);
  color: white;
  border-radius: 10px;
  overflow: hidden;
}

.cctv-preview-label {
  padding: 6px 8px 0;
  font-size: 11px;
  font-weight: 700;
}

.cctv-preview-image {
  height: 86px;
  margin: 6px 8px;
  border-radius: 8px;
  background:
    linear-gradient(rgba(0, 0, 0, 0.12), rgba(0, 0, 0, 0.12)),
    url('../assets/login-bg.jpg');
  background-size: cover;
  background-position: center;
}

.cctv-preview-footer {
  padding: 0 8px 8px;
  font-size: 11px;
}

.traffic-density-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-top: 10px;
}

.density-info-box {
  background: rgba(255, 255, 255, 0.94);
  border-radius: 12px;
  padding: 12px;
}

.density-title {
  font-size: 13px;
  margin-bottom: 4px;
}

.density-sub {
  font-size: 22px;
  font-weight: 800;
}

.density-gauge-wrap {
  background: rgba(255, 255, 255, 0.94);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.density-gauge {
  width: 120px;
  height: 68px;
  border-top-left-radius: 120px;
  border-top-right-radius: 120px;
  background: conic-gradient(
    from 180deg,
    #47d46a 0deg 70deg,
    #65cbe5 70deg 140deg,
    #d7dadd 140deg 180deg
  );
  position: relative;
  overflow: hidden;
}

.density-gauge-inner {
  position: absolute;
  left: 14px;
  right: 14px;
  bottom: -28px;
  height: 82px;
  background: white;
  border-radius: 50%;
  text-align: center;
  padding-top: 20px;
}

.density-text-main {
  font-size: 18px;
  font-weight: 800;
}

.density-text-sub {
  font-size: 16px;
}

.report-panel {
  right: 12px;
  top: 58px;
  width: 250px;
}

.kpi-stack {
  display: grid;
  grid-template-columns: 1fr;
  gap: 8px;
  margin-bottom: 10px;
}

.kpi-box {
  background: rgba(255, 255, 255, 0.94);
  border-radius: 10px;
  padding: 10px;
}

.kpi-label {
  font-size: 12px;
  color: #666;
  margin-bottom: 4px;
}

.kpi-value {
  font-size: 20px;
  font-weight: 800;
}

.mini-chart-box {
  background: rgba(255, 255, 255, 0.94);
  border-radius: 10px;
  padding: 10px;
  margin-bottom: 10px;
}

.mini-chart-title {
  font-size: 12px;
  font-weight: 700;
  margin-bottom: 6px;
}

.mini-chart {
  width: 100%;
  height: 72px;
  background: #f8fbff;
  border-radius: 8px;
}

.bar-chart {
  height: 82px;
  display: flex;
  align-items: flex-end;
  gap: 6px;
}

.bar-item {
  flex: 1;
  display: flex;
  align-items: flex-end;
}

.bar {
  width: 100%;
  background: #5d9cec;
  border-radius: 6px 6px 0 0;
}

.alert-list-box {
  background: rgba(255, 255, 255, 0.94);
  border-radius: 10px;
  padding: 10px;
  margin-bottom: 10px;
}

.alert-list-title {
  font-size: 12px;
  font-weight: 700;
  margin-bottom: 6px;
}

.empty-alert-text {
  font-size: 12px;
  color: #777;
}

.alert-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 84px;
  overflow-y: auto;
}

.alert-item {
  background: #f3f6fb;
  border-radius: 8px;
  padding: 8px;
  font-size: 11px;
  font-weight: 600;
}

.report-btn {
  width: 100%;
  height: 38px;
  border: none;
  border-radius: 10px;
  background: #f3f3f3;
  cursor: pointer;
  font-weight: 700;
  font-size: 12px;
}

.center-overlay {
  position: absolute;
  left: 334px;
  right: 274px;
  top: 58px;
  bottom: 12px;
  z-index: 5;
}


.signal-badge {
  position: absolute;
  left: 50%;
  top: 10px;
  transform: translateX(-50%);
  background: rgba(30, 30, 30, 0.82);
  color: white;
  padding: 10px 16px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 800;
  z-index: 30;
}

.leaflet-map-wrap {
  position: absolute;
  inset: 0;
  border-radius: 18px;
  overflow: hidden;
  border: 2px solid rgba(255, 255, 255, 0.7);
  box-shadow: 0 10px 22px rgba(0, 0, 0, 0.15);
}

.leaflet-map {
  width: 100%;
  height: 100%;
}

.map-empty-state {
  position: absolute;
  inset: 0;
  background: transparent;
  border: none;
}

.pip-card {
  position: absolute;
  right: 16px;
  bottom: 58px;
  width: 150px;
  background: rgba(30, 30, 30, 0.8);
  border-radius: 10px;
  overflow: hidden;
  z-index: 25;
}

.pip-title {
  padding: 6px 8px;
  color: white;
  font-weight: 700;
  font-size: 12px;
}

.pip-image {
  height: 82px;
  background:
    linear-gradient(rgba(0, 0, 0, 0.08), rgba(0, 0, 0, 0.08)),
    url('../assets/login-bg.jpg');
  background-size: cover;
  background-position: center;
}

.center-control-bar {
  position: absolute;
  left: 50%;
  bottom: 14px;
  transform: translateX(-50%);
  display: flex;
  gap: 6px;
  z-index: 30;
}

.center-control-bar button {
  min-width: 42px;
  height: 36px;
  border: none;
  border-radius: 8px;
  background: rgba(24, 24, 24, 0.85);
  color: white;
  cursor: pointer;
}

.center-control-bar button.active {
  background: #6d2c2c;
}

.route-debug-box {
  position: absolute;
  left: 16px;
  bottom: 16px;
  z-index: 30;
  background: rgba(0, 0, 0, 0.72);
  color: white;
  padding: 8px 12px;
  border-radius: 10px;
  font-size: 12px;
}

.violation-panel {
  left: 12px;
  bottom: 12px;
  width: 310px;
  height: 300px;
  display: flex;
  flex-direction: column;
}

.table-subtitle {
  margin-bottom: 8px;
  font-weight: 700;
  color: #444;
  font-size: 12px;
}

.violation-table-wrap {
  flex: 1;
  overflow: hidden;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.94);
}

.violation-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}

.violation-table thead {
  display: table;
  width: 100%;
  table-layout: fixed;
}

.violation-table tbody {
  display: block;
  height: 170px;
  overflow: hidden;
}

.violation-table tbody tr {
  display: table;
  width: 100%;
  table-layout: fixed;
}

.violation-table th,
.violation-table td {
  padding: 8px 5px;
  border-bottom: 1px solid #ececec;
  font-size: 12px;
  text-align: center;
  word-break: keep-all;
}

.violation-table th:nth-child(1),
.violation-table td:nth-child(1) {
  width: 24%;
}

.violation-table th:nth-child(2),
.violation-table td:nth-child(2) {
  width: 22%;
}

.violation-table th:nth-child(3),
.violation-table td:nth-child(3) {
  width: 18%;
}

.violation-table th:nth-child(4),
.violation-table td:nth-child(4) {
  width: 16%;
}

.violation-table th:nth-child(5),
.violation-table td:nth-child(5) {
  width: 20%;
}

.action-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
  align-items: center;
  justify-content: center;
}

.approve-btn,
.reject-btn {
  width: 46px;
  border: none;
  border-radius: 8px;
  padding: 5px 6px;
  cursor: pointer;
  font-weight: 700;
  font-size: 11px;
}

.approve-btn {
  background: #39c466;
  color: white;
}

.reject-btn {
  background: #ff3a3a;
  color: white;
}

.violation-pagination {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 10px;
  gap: 8px;
}

.page-btn {
  flex: 1;
  height: 34px;
  border: none;
  border-radius: 10px;
  background: #efefef;
  cursor: pointer;
  font-weight: 700;
}

.page-btn:disabled {
  background: #d8d8d8;
  cursor: default;
}

.page-info {
  min-width: 72px;
  text-align: center;
  font-size: 12px;
  font-weight: 800;
}

.lifecycle-panel {
  right: 12px;
  bottom: 12px;
  width: 250px;
}

.lifecycle-gauge-row {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
}

.device-gauge-box {
  flex: 1;
  background: rgba(255, 255, 255, 0.94);
  border-radius: 12px;
  padding: 10px;
  text-align: center;
}

.device-gauge {
  width: 70px;
  height: 70px;
  margin: 0 auto 8px;
  border-radius: 50%;
  background: conic-gradient(#5ad567 0deg 230deg, #d9dcdf 230deg 360deg);
  position: relative;
}

.device-gauge.warning {
  background: conic-gradient(#f0b23d 0deg 250deg, #d9dcdf 250deg 360deg);
}

.device-gauge::after {
  content: '';
  position: absolute;
  inset: 10px;
  background: white;
  border-radius: 50%;
}

.device-label {
  font-weight: 700;
  line-height: 1.3;
  font-size: 11px;
}

.device-alert-box {
  background: #7e1d1d;
  color: white;
  border-radius: 10px;
  padding: 10px;
  text-align: center;
  font-weight: 800;
  margin-bottom: 10px;
  font-size: 12px;
}

.maintenance-text {
  background: rgba(255, 255, 255, 0.82);
  border-radius: 10px;
  padding: 10px;
  text-align: center;
  font-size: 12px;
  margin-bottom: 10px;
}

.repair-btn {
  width: 100%;
  height: 38px;
  border: none;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.72);
  cursor: pointer;
  font-weight: 700;
  font-size: 12px;
}

.map-data-panel {
  right: 12px;
  top: 110px;
  width: 320px;
  max-height: 620px;
  overflow: hidden;
  z-index: 40;
}

.map-panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
  gap: 8px;
}

.map-panel-header-actions {
  display: flex;
  gap: 6px;
}

.map-panel-sub {
  font-size: 12px;
  color: #666;
  margin-bottom: 10px;
}

.reload-btn,
.close-panel-btn {
  border: none;
  color: white;
  padding: 6px 10px;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 700;
  font-size: 12px;
}

.reload-btn {
  background: #1389ff;
}

.close-panel-btn {
  background: #666;
}

.map-status {
  background: rgba(255, 255, 255, 0.88);
  border-radius: 10px;
  padding: 10px;
  font-size: 12px;
}

.map-status.error {
  color: #c62828;
}

.map-list {
  display: grid;
  grid-template-columns: 1fr;
  gap: 8px;
  max-height: 220px;
  overflow-y: auto;
  margin-bottom: 10px;
}

.map-item {
  background: rgba(255, 255, 255, 0.92);
  border-radius: 10px;
  padding: 10px;
  cursor: pointer;
  border: 2px solid transparent;
}

.map-item:hover {
  border-color: #5d9cec;
}

.map-item-title {
  font-weight: 800;
  margin-bottom: 6px;
  font-size: 13px;
}

.map-item-row {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 12px;
  margin-bottom: 3px;
}

.selected-map-box {
  background: rgba(255, 255, 255, 0.92);
  border-radius: 10px;
  padding: 10px;
}

.selected-title {
  font-size: 12px;
  color: #666;
  margin-bottom: 4px;
}

.selected-name {
  font-size: 16px;
  font-weight: 800;
  margin-bottom: 8px;
}

.selected-equipment-title {
  font-weight: 700;
  margin-bottom: 6px;
  font-size: 12px;
}

.selected-equipment-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.selected-equipment-item {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  background: #f5f7fb;
  padding: 7px 8px;
  border-radius: 8px;
  font-size: 12px;
}

.no-equipment-text {
  color: #777;
  font-size: 12px;
}

.selected-map-actions {
  margin-top: 10px;
  display: flex;
  gap: 8px;
}

.priority-open-btn {
  flex: 1;
  height: 36px;
  border: none;
  border-radius: 10px;
  background: #1389ff;
  color: white;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}

.priority-open-btn.danger {
  background: #7e1d1d;
}

.emergency-modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: rgba(0, 0, 0, 0.28);
  display: flex;
  align-items: center;
  justify-content: center;
}

.emergency-modal {
  position: relative;
  width: 320px;
  padding: 20px 18px 18px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 16px 36px rgba(0, 0, 0, 0.24);
  text-align: center;
}

.emergency-modal h3 {
  margin: 0 0 10px;
  font-size: 18px;
}

.emergency-close-btn {
  position: absolute;
  right: 10px;
  top: 10px;
  width: 30px;
  height: 30px;
  border: none;
  border-radius: 50%;
  background: #f1f1f1;
  cursor: pointer;
  font-size: 14px;
  font-weight: 700;
}

.emergency-chip {
  display: inline-block;
  background: #ff2e2e;
  color: white;
  padding: 6px 16px;
  border-radius: 999px;
  font-weight: 800;
  margin: 6px 0 10px;
  font-size: 12px;
}

.emergency-message {
  font-size: 12px;
  margin-bottom: 10px;
}

.emergency-location-text {
  margin: 8px 0 12px;
  font-size: 13px;
  color: #333;
  line-height: 1.5;
}

.emergency-main-btn {
  width: 220px;
  height: 42px;
  border: none;
  border-radius: 12px;
  background: linear-gradient(#fefefe, #d9d9d9);
  font-weight: 800;
  font-size: 15px;
  cursor: pointer;
  box-shadow: 0 6px 12px rgba(0, 0, 0, 0.16);
}

.emergency-eta {
  margin: 12px 0;
  font-size: 13px;
}

.emergency-bottom-alert {
  background: #5a1e1e;
  color: #ff8072;
  padding: 10px;
  border-radius: 10px;
  font-weight: 700;
  font-size: 11px;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

:deep(.custom-intersection-marker) {
  background: transparent;
  border: none;
}

:deep(.intersection-marker-dot) {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #1389ff;
  border: 3px solid white;
  box-shadow: 0 0 10px rgba(19, 137, 255, 0.45);
}

:deep(.custom-emergency-marker) {
  background: transparent;
  border: none;
}

:deep(.emergency-vehicle-marker) {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  box-shadow: 0 0 12px rgba(255, 46, 46, 0.55);
  border: 2px solid #ff2e2e;
}

@media (max-width: 1500px) {
  .traffic-dashboard {
    min-height: 1500px;
    height: auto;
  }

  .traffic-intel,
  .report-panel,
  .violation-panel,
  .lifecycle-panel,
  .map-data-panel {
    position: relative;
    left: auto;
    right: auto;
    top: auto;
    bottom: auto;
    width: auto;
    height: auto;
    margin-bottom: 14px;
  }

  .center-overlay {
    position: relative;
    left: auto;
    right: auto;
    top: auto;
    bottom: auto;
    min-height: 560px;
    margin-bottom: 14px;
  }

  .violation-table tbody {
    height: auto;
  }
}
</style>