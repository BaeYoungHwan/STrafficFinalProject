<template>
  <div class="cctv-section">
    <div class="top-bar">
      <div class="view-info">
        <span>현재 보기: {{ pageSize }}분할</span>
        <span>|</span>
        <span>페이지: {{ currentPage }} / {{ totalPages }}</span>
      </div>

      <div class="top-actions">
        <button v-if="isFocusMode" class="mode-btn" @click="exitFocusMode">전체 보기</button>
      </div>
    </div>

    <div v-if="isFocusMode && selectedCamera" class="focus-view">
      <div class="focus-header">
        <div>
          <strong>{{ selectedCamera.name }}</strong>
          <span class="focus-status">{{ selectedCamera.status }}</span>
        </div>

        <div class="focus-buttons">
          <button class="focus-btn" @click="prevCamera">이전 카메라</button>
          <button class="focus-btn" @click="nextCamera">다음 카메라</button>
          <button class="focus-btn primary" @click="exitFocusMode">분할 보기</button>
        </div>
      </div>

      <div class="focus-body">
        <img :src="selectedCamera.thumbnailUrl" :alt="selectedCamera.name" class="focus-image" />
        <div class="focus-overlay">LIVE VIEW</div>
      </div>
    </div>

    <div v-else class="grid-view">
      <div class="camera-grid" :class="gridClass">
        <CctvTile
          v-for="camera in visibleCameras"
          :key="camera.id"
          :camera="camera"
          :mode="displayMode"
          @select="selectCamera"
        />
      </div>

      <div class="pagination-bar">
        <button class="page-btn" @click="prevPage" :disabled="currentPage === 1">이전</button>
        <span class="page-text">{{ currentPage }} / {{ totalPages }}</span>
        <button class="page-btn" @click="nextPage" :disabled="currentPage === totalPages">다음</button>
      </div>
    </div>

    <div class="zoom-bar">
      <button class="zoom-btn" @click="decreaseZoom">-</button>

      <input
        class="zoom-slider"
        type="range"
        min="4"
        max="16"
        step="6"
        v-model="zoomLevel"
      />

      <button class="zoom-btn" @click="increaseZoom">+</button>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import CctvTile from './CctvTile.vue'

const props = defineProps({
  cameras: {
    type: Array,
    required: true,
  },
})

const zoomLevel = ref(16)
const currentPage = ref(1)
const isFocusMode = ref(false)
const selectedCamera = ref(null)

const pageSize = computed(() => {
  if (Number(zoomLevel.value) >= 16) return 16
  if (Number(zoomLevel.value) >= 10) return 10
  return 4
})

const displayMode = computed(() => {
  if (pageSize.value >= 16) return 'thumbnail'
  if (pageSize.value > 4) return 'preview'
  return 'stream'
})

const totalPages = computed(() => {
  return Math.max(1, Math.ceil(props.cameras.length / pageSize.value))
})

const pagedCameras = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return props.cameras.slice(start, end)
})

const visibleCameras = computed(() => pagedCameras.value)

const gridClass = computed(() => {
  if (pageSize.value >= 16) return 'grid-4'
  if (pageSize.value > 4) return 'grid-3'
  return 'grid-2'
})

watch(pageSize, () => {
  currentPage.value = 1
  isFocusMode.value = false
  selectedCamera.value = null
})

watch(currentPage, () => {
  if (currentPage.value > totalPages.value) {
    currentPage.value = totalPages.value
  }
})

const decreaseZoom = () => {
  if (Number(zoomLevel.value) > 4) {
    zoomLevel.value = Number(zoomLevel.value) - 6
  }
}

const increaseZoom = () => {
  if (Number(zoomLevel.value) < 16) {
    zoomLevel.value = Number(zoomLevel.value) + 6
  }
}

const prevPage = () => {
  if (currentPage.value > 1) {
    currentPage.value -= 1
  }
}

const nextPage = () => {
  if (currentPage.value < totalPages.value) {
    currentPage.value += 1
  }
}

const selectCamera = (camera) => {
  selectedCamera.value = camera
  isFocusMode.value = true
}

const exitFocusMode = () => {
  isFocusMode.value = false
}

const selectedIndex = computed(() => {
  if (!selectedCamera.value) return -1
  return props.cameras.findIndex((cam) => cam.id === selectedCamera.value.id)
})

const prevCamera = () => {
  if (selectedIndex.value > 0) {
    selectedCamera.value = props.cameras[selectedIndex.value - 1]
  }
}

const nextCamera = () => {
  if (selectedIndex.value >= 0 && selectedIndex.value < props.cameras.length - 1) {
    selectedCamera.value = props.cameras[selectedIndex.value + 1]
  }
}
</script>

<style scoped>
.cctv-section {
  width: 100%;
}

.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
  gap: 12px;
}

.view-info {
  display: flex;
  gap: 8px;
  align-items: center;
  color: #444;
  font-size: 14px;
}

.mode-btn {
  height: 38px;
  padding: 0 16px;
  border: none;
  border-radius: 10px;
  background: #1389ff;
  color: white;
  cursor: pointer;
  font-weight: 600;
}

.grid-view {
  width: 100%;
}

.camera-grid {
  display: grid;
  gap: 8px;
  margin-bottom: 16px;
}

.camera-grid.grid-4 {
  grid-template-columns: repeat(4, 1fr);
}

.camera-grid.grid-3 {
  grid-template-columns: repeat(3, 1fr);
}

.camera-grid.grid-2 {
  grid-template-columns: repeat(2, 1fr);
}

.pagination-bar {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  margin-bottom: 14px;
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

.page-text {
  font-size: 15px;
  font-weight: 600;
}

.focus-view {
  background: #f4f4f4;
  border-radius: 18px;
  padding: 16px;
  margin-bottom: 16px;
  box-shadow: 0 8px 18px rgba(0, 0, 0, 0.06);
}

.focus-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.focus-status {
  margin-left: 10px;
  color: #666;
  font-size: 14px;
}

.focus-buttons {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.focus-btn {
  height: 36px;
  padding: 0 12px;
  border: none;
  border-radius: 10px;
  background: white;
  cursor: pointer;
}

.focus-btn.primary {
  background: #1389ff;
  color: white;
}

.focus-body {
  position: relative;
  height: 520px;
  border-radius: 14px;
  overflow: hidden;
  background: #cfd5db;
}

.focus-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.focus-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 34px;
  font-weight: 800;
  background: rgba(0, 0, 0, 0.22);
}

.zoom-bar {
  display: flex;
  align-items: center;
  gap: 14px;
  margin: 10px 0 18px;
}

.zoom-btn {
  width: 42px;
  height: 42px;
  border: none;
  border-radius: 50%;
  background: white;
  font-size: 28px;
  cursor: pointer;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.08);
}

.zoom-slider {
  flex: 1;
  accent-color: #999;
}

@media (max-width: 1200px) {
  .camera-grid.grid-4,
  .camera-grid.grid-3 {
    grid-template-columns: repeat(2, 1fr);
  }

  .camera-grid.grid-2 {
    grid-template-columns: 1fr;
  }

  .focus-body {
    height: 360px;
  }
}

@media (max-width: 768px) {
  .top-bar,
  .focus-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .focus-body {
    height: 260px;
  }
}
</style>