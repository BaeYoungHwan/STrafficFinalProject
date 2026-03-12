<template>
  <div class="camera-item">
    <div class="camera-header">
      <span>{{ camera.name }}</span>
      <span>{{ camera.status }}</span>
    </div>

    <div v-if="mode !== 'stream'" class="camera-thumb-wrap">
      <img :src="camera.thumbnailUrl" :alt="camera.name" class="camera-thumb" />
      <div class="camera-mode-badge">{{ modeLabel }}</div>
    </div>

    <div v-else class="camera-stream-wrap">
      <img :src="camera.thumbnailUrl" :alt="camera.name" class="camera-thumb" />
      <div class="stream-overlay">STREAM READY</div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  camera: {
    type: Object,
    required: true,
  },
  mode: {
    type: String,
    default: 'thumbnail',
  },
})

const modeLabel = computed(() => {
  if (props.mode === 'stream') return '실시간'
  if (props.mode === 'preview') return '미리보기'
  return '썸네일'
})
</script>

<style scoped>
.camera-item {
  border: 1px solid #2f3842;
  border-radius: 6px;
  overflow: hidden;
  background: #d9dde2;
}

.camera-header {
  background: #1f2832;
  color: white;
  font-size: 12px;
  padding: 6px 8px;
  font-weight: 700;
  display: flex;
  justify-content: space-between;
}

.camera-thumb-wrap,
.camera-stream-wrap {
  position: relative;
  height: 120px;
  background: #cfd5db;
}

.camera-thumb {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  filter: grayscale(10%);
}

.camera-mode-badge {
  position: absolute;
  right: 6px;
  bottom: 6px;
  background: rgba(0, 0, 0, 0.65);
  color: white;
  font-size: 11px;
  padding: 3px 6px;
  border-radius: 999px;
}

.stream-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 15px;
  font-weight: 700;
  background: rgba(0, 0, 0, 0.28);
}
</style>