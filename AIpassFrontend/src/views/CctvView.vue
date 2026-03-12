<template>
  <section class="cctv-page">
    <div class="cctv-header">
      <h2>CCTV</h2>
      <p>전체 CCTV 상세 화면 페이지입니다. 카메라를 클릭하면 크게 볼 수 있습니다.</p>
    </div>

    <CctvGrid :cameras="cameras" />
  </section>
</template>

<script setup>
import CctvGrid from '../components/CctvGrid.vue'
import camImg from '../assets/login-bg.jpg'

const cameras = [
  { id: 1, name: 'CAM 01', status: '혼잡', thumbnailUrl: camImg, streamUrl: '' },
  { id: 2, name: 'CAM 02', status: '원활', thumbnailUrl: camImg, streamUrl: '' },
  { id: 3, name: 'CAM 03', status: '혼잡', thumbnailUrl: camImg, streamUrl: '' },
  { id: 4, name: 'CAM 04', status: '정상', thumbnailUrl: camImg, streamUrl: '' },
  { id: 5, name: 'CAM 05', status: '원활', thumbnailUrl: camImg, streamUrl: '' },
  { id: 6, name: 'CAM 06', status: '혼잡', thumbnailUrl: camImg, streamUrl: '' },
  { id: 7, name: 'CAM 07', status: '정상', thumbnailUrl: camImg, streamUrl: '' },
  { id: 8, name: 'CAM 08', status: '정상', thumbnailUrl: camImg, streamUrl: '' },
  { id: 9, name: 'CAM 09', status: '원활', thumbnailUrl: camImg, streamUrl: '' },
  { id: 10, name: 'CAM 10', status: '원활', thumbnailUrl: camImg, streamUrl: '' },
  { id: 11, name: 'CAM 11', status: '혼잡', thumbnailUrl: camImg, streamUrl: '' },
  { id: 12, name: 'CAM 12', status: '정상', thumbnailUrl: camImg, streamUrl: '' },
  { id: 13, name: 'CAM 13', status: '원활', thumbnailUrl: camImg, streamUrl: '' },
  { id: 14, name: 'CAM 14', status: '정상', thumbnailUrl: camImg, streamUrl: '' },
  { id: 15, name: 'CAM 15', status: '원활', thumbnailUrl: camImg, streamUrl: '' },
  { id: 16, name: 'CAM 16', status: '정상', thumbnailUrl: camImg, streamUrl: '' },
]
</script>

<style scoped>
.cctv-page {
  width: 100%;
}

.cctv-header {
  margin-bottom: 16px;
}

.cctv-header h2 {
  margin: 0 0 8px;
  font-size: 24px;
}

.cctv-header p {
  margin: 0;
  color: #666;
  font-size: 15px;
}
</style>