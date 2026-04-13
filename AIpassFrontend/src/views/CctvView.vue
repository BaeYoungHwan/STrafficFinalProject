<template>
  <div class="cctv-page">

    <!-- 페이지 헤더 -->
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">실시간 CCTV</h2>
        <span class="count-badge">{{ filteredList.length }}개 채널</span>
      </div>
      <button class="btn-refresh" @click="fetchList" :disabled="loading">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/>
          <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
        </svg>
        새로 고침
      </button>
    </div>


    <!-- 로딩 스켈레톤 -->
    <div v-if="loading" class="cctv-grid">
      <div v-for="i in 12" :key="i" class="cctv-card skeleton"></div>
    </div>

    <!-- 빈 상태 -->
    <div v-else-if="filteredList.length === 0" class="empty-state">
      활성화된 CCTV가 없습니다.
    </div>

    <!-- CCTV 그리드 -->
    <div v-else class="cctv-grid">
      <div
        v-for="cctv in filteredList"
        :key="cctv.cctvId"
        class="cctv-card"
        :class="{ hovered: hoveredId === cctv.cctvId }"
        :data-cctv-id="cctv.cctvId"
        :ref="el => observeCard(el, cctv.cctvId)"
        @mouseenter="hoveredId = cctv.cctvId"
        @mouseleave="hoveredId = null"
        @click="openModal(cctv)"
      >
        <span class="live-badge">● LIVE</span>
        <video
          :ref="el => setVideoRef(el, cctv.cctvId)"
          class="cctv-stream"
          autoplay
          muted
          playsinline
        ></video>

        <div class="cctv-overlay">
          <span class="cctv-name">{{ cctv.cctvName }}</span>
          <div class="cctv-meta">
            <span v-if="cctv.roadName">📍 {{ cctv.roadName }}</span>
            <span v-if="cctv.updatedAt">{{ cctv.updatedAt }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 확대 모달 -->
    <Teleport to="body">
      <div v-if="selectedCctv" class="modal-backdrop" @click.self="closeModal">
        <div class="modal-box">
          <div class="modal-header">
            <div class="modal-title-wrap">
              <span class="live-badge">● LIVE</span>
              <span class="modal-name">{{ selectedCctv.cctvName }}</span>
              <span v-if="selectedCctv.roadName" class="modal-road">📍 {{ selectedCctv.roadName }}</span>
            </div>
            <button class="modal-close" @click="closeModal">✕</button>
          </div>
          <div class="modal-video-wrap">
            <canvas ref="modalCanvas" class="modal-canvas"></canvas>
            <div ref="modalSpinner" class="modal-spinner">
              <div class="spinner-ring"></div>
              <span>스트림 연결 중...</span>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import Hls from 'hls.js'
import api from '../api'

const cctvList = ref([])
const loading = ref(false)
const hoveredId = ref(null)

const videoRefs = ref({})
const hlsMap = {}

// ─── 모달 상태 ───────────────────────────────────────────────────────────────
const selectedCctv = ref(null)
const modalCanvas = ref(null)
const modalSpinner = ref(null)
let modalHls = null
let modalRafId = null

// ─── Intersection Observer ────────────────────────────────────────────────────
const cardRefs = {}
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    const cctvId = entry.target.dataset.cctvId
    if (entry.isIntersecting) {
      initHlsForCard(cctvId)
    } else {
      destroyHlsForCard(cctvId)
    }
  })
}, { threshold: 0.1 })

const observeCard = (el, cctvId) => {
  if (el) {
    cardRefs[cctvId] = el
    observer.observe(el)
  } else {
    if (cardRefs[cctvId]) observer.unobserve(cardRefs[cctvId])
    delete cardRefs[cctvId]
    destroyHlsForCard(cctvId)
  }
}

// ─── 계산 속성 ────────────────────────────────────────────────────────────────
const filteredList = computed(() => cctvList.value.slice(0, 12))

// ─── video ref 등록 ───────────────────────────────────────────────────────────
const setVideoRef = (el, cctvId) => {
  if (el) videoRefs.value[cctvId] = el
  else delete videoRefs.value[cctvId]
}

// ─── HLS 개별 제어 ────────────────────────────────────────────────────────────
const initHlsForCard = (cctvId) => {
  const cctv = filteredList.value.find(c => c.cctvId === cctvId)
  const video = videoRefs.value[cctvId]
  if (!cctv || !video || !cctv.streamUrl) return
  if (hlsMap[cctvId]) return

  if (Hls.isSupported()) {
    const hls = new Hls({ enableWorker: false })
    hls.loadSource(cctv.streamUrl)
    hls.attachMedia(video)
    hlsMap[cctvId] = hls
  } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
    video.src = cctv.streamUrl
  }
}

const destroyHlsForCard = (cctvId) => {
  if (hlsMap[cctvId]) {
    hlsMap[cctvId].destroy()
    delete hlsMap[cctvId]
  }
  const video = videoRefs.value[cctvId]
  if (video) video.src = ''
}

// ─── HLS 전체 제어 ────────────────────────────────────────────────────────────
const destroyHls = () => {
  Object.keys(hlsMap).forEach(cctvId => destroyHlsForCard(cctvId))
}

// ─── API 호출 ─────────────────────────────────────────────────────────────────
const fetchList = async () => {
  destroyHls()
  loading.value = true
  try {
    const res = await api.get('/cctv/list')
    cctvList.value = res.data.data || []
  } catch (e) {
    cctvList.value = []
  } finally {
    loading.value = false
  }
}

// ─── 모달 제어 ────────────────────────────────────────────────────────────────
const openModal = async (cctv) => {
  selectedCctv.value = cctv
  await nextTick()

  const canvas = modalCanvas.value
  if (!canvas) return

  const cardVideo = videoRefs.value[cctv.cctvId]
  if (!cardVideo) return

  // 카드 크기에 맞게 canvas 초기화
  canvas.width = cardVideo.videoWidth || 1280
  canvas.height = cardVideo.videoHeight || 720
  canvas.style.opacity = '1'
  if (modalSpinner.value) modalSpinner.value.style.opacity = '0'

  // 카드 HLS 를 새로 열지 않고 RAF 로 카드 video 프레임을 canvas 에 계속 그림
  // (ITS 서버 연결 한도 초과 방지 — 12개 카드 스트림이 이미 활성 상태)
  if (modalRafId) cancelAnimationFrame(modalRafId)
  const draw = () => {
    if (!selectedCctv.value) return
    if (cardVideo.readyState >= 2) {
      canvas.getContext('2d').drawImage(cardVideo, 0, 0, canvas.width, canvas.height)
    }
    modalRafId = requestAnimationFrame(draw)
  }
  modalRafId = requestAnimationFrame(draw)
}

const closeModal = () => {
  if (modalRafId) { cancelAnimationFrame(modalRafId); modalRafId = null }
  if (modalHls) { modalHls.destroy(); modalHls = null }
  if (modalCanvas.value) modalCanvas.value.style.opacity = '0'
  if (modalSpinner.value) modalSpinner.value.style.opacity = '0'
  selectedCctv.value = null
}

// ─── Page Visibility API ──────────────────────────────────────────────────────
const onVisibilityChange = () => {
  if (document.hidden) {
    destroyHls()
  } else {
    Object.entries(cardRefs).forEach(([cctvId, el]) => {
      const rect = el.getBoundingClientRect()
      const inViewport = rect.top < window.innerHeight && rect.bottom > 0
      if (inViewport) initHlsForCard(cctvId)
    })
  }
}

// ─── Keyboard 이벤트 ──────────────────────────────────────────────────────────
const onKeydown = (e) => {
  if (e.key === 'Escape') closeModal()
}

// ─── filteredList 변경 시 observer 재등록 ─────────────────────────────────────
watch(filteredList, () => {
  Object.entries(cardRefs).forEach(([, el]) => observer.unobserve(el))
  Object.keys(cardRefs).forEach(k => delete cardRefs[k])
  destroyHls()
  // observeCard는 :ref 바인딩으로 nextTick 후 자동 재등록됨
})

// ─── 생명주기 ─────────────────────────────────────────────────────────────────
onMounted(() => {
  fetchList()
  document.addEventListener('visibilitychange', onVisibilityChange)
  document.addEventListener('keydown', onKeydown)
})

onBeforeUnmount(() => {
  if (modalRafId) { cancelAnimationFrame(modalRafId); modalRafId = null }
  destroyHls()
  closeModal()
  observer.disconnect()
  document.removeEventListener('visibilitychange', onVisibilityChange)
  document.removeEventListener('keydown', onKeydown)
})
</script>

<style scoped>
/* 페이지 */
.cctv-page {
  padding: 28px 32px;
  background: transparent;
  min-height: 100%;
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', sans-serif;
}

/* 헤더 */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 0;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  color: #1A1A2E;
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif;
}

.count-badge {
  margin-left: 10px;
  background: #E8F1FB;
  color: #1A6DCC;
  font-size: 12px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: 10px;
}

.btn-refresh {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #1A6DCC;
  color: #fff;
  border: none;
  border-radius: 10px;
  padding: 9px 18px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
}

.btn-refresh:hover {
  background: #1457A8;
  transform: translateY(-1px);
}

.btn-refresh:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}


/* 그리드 */
.cctv-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  overflow: visible;
  position: relative;
}

/* 카드 */
.cctv-card {
  position: relative;
  aspect-ratio: 16 / 9;
  border-radius: 16px;
  overflow: hidden;
  cursor: pointer;
  background: #1A1A2E;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  transition:
    transform 0.22s cubic-bezier(0.34, 1.56, 0.64, 1),
    box-shadow 0.22s ease,
    border-color 0.15s ease;
  border: 2px solid transparent;
  z-index: 1;
}

/* 호버 시 카드 확대 */
.cctv-card.hovered {
  transform: scale(1.55);
  z-index: 10;
  border-color: #1A6DCC;
  border-width: 2.5px;
  box-shadow: 0 16px 48px rgba(26, 109, 204, 0.5);
}

/* LIVE 뱃지 */
.live-badge {
  position: absolute;
  top: 8px;
  left: 10px;
  background: rgba(239, 68, 68, 0.88);
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: 6px;
  z-index: 2;
  letter-spacing: 0.3px;
}

/* 스트림 비디오 */
.cctv-stream {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

/* 이름 오버레이 */
.cctv-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: linear-gradient(transparent, rgba(0, 0, 0, 0.72));
  padding: 24px 12px 10px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  transition: padding 0.22s ease, background 0.22s ease;
}

.cctv-card.hovered .cctv-overlay {
  padding: 32px 12px 14px;
  background: linear-gradient(transparent, rgba(0, 0, 0, 0.85));
}

.cctv-name {
  font-size: 12px;
  font-weight: 600;
  color: #fff;
  transition: font-size 0.22s ease;
}

.cctv-card.hovered .cctv-name {
  font-size: 13px;
}

/* 부가 정보 — 호버 시 표시 */
.cctv-meta {
  display: none;
  flex-direction: column;
  gap: 2px;
  margin-top: 4px;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.8);
}

.cctv-card.hovered .cctv-meta {
  display: flex;
}

/* 스켈레톤 */
.skeleton {
  background: linear-gradient(90deg, #e0e7ef 25%, #f0f4fa 50%, #e0e7ef 75%);
  background-size: 200% 100%;
  animation: shimmer 1.4s infinite;
  cursor: default;
  border: none !important;
}

@keyframes shimmer {
  0%   { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* 빈 상태 */
.empty-state {
  text-align: center;
  padding: 80px 20px;
  color: #6B7280;
  font-size: 15px;
}

/* 반응형 */
@media (max-width: 1100px) {
  .cctv-grid { grid-template-columns: repeat(3, 1fr); }
}
@media (max-width: 800px) {
  .cctv-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 500px) {
  .cctv-grid { grid-template-columns: 1fr; }
}

/* ─── 모달 ─────────────────────────────────────────────────────────────────── */
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
  width: 80vw;
  max-width: 1200px;
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

.modal-name {
  font-size: 15px;
  font-weight: 700;
  color: #fff;
}

.modal-road {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
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

.modal-video-wrap {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  background: #000;
}

.modal-video {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: cover;
}

/* 카드 라이브 스트림을 RAF 로 복사하는 canvas — 모달의 실제 디스플레이 */
.modal-canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  opacity: 0;
  pointer-events: none;
}

/* 로딩 스피너 */
.modal-spinner {
  position: absolute;
  bottom: 16px;
  right: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(0, 0, 0, 0.55);
  padding: 6px 12px;
  border-radius: 20px;
  opacity: 0;
  transition: opacity 0.3s ease;
  pointer-events: none;
}

.modal-spinner span {
  color: rgba(255,255,255,0.85);
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0.3px;
}

.spinner-ring {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255,255,255,0.25);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  flex-shrink: 0;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
