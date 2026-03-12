<template>
  <section class="dashboard-page">

    <div class="camera-grid">
      <div v-for="cam in visibleCameras" :key="cam.id" class="camera-item">
        <div class="camera-header">
          <span>CAM {{ String(cam.id).padStart(2, '0') }}</span>
          <span>{{ cam.status }}</span>
        </div>
        <div class="camera-body" :style="{ backgroundImage: `url(${cam.image})` }"></div>
      </div>
    </div>

    <div class="dashboard-cards">

      <!-- 교통량 -->
      <div class="info-card">
        <h3>누적 교통량</h3>

        <div class="card-box">
          <p>
            오늘 누적 교통량 :
            <strong>{{ dashboard.todayTrafficTotal }}대</strong>
          </p>

          <p>
            전일 대비 :
            <strong>{{ dashboard.trafficChangeRate }}%</strong>
          </p>
        </div>
      </div>

      <!-- 미처리 단속 -->
      <div class="info-card clickable" @click="goViolation">
        <h3>미처리 단속</h3>

        <div class="card-box center-box">
          <div class="main-count red">
            {{ dashboard.unprocessedCount }}건
          </div>

          <div class="sub-guide">
            클릭 시 단속 내역 이동
          </div>
        </div>
      </div>

      <!-- 위험 장비 -->
      <div class="info-card clickable" @click="goPredict">
        <h3>고장 위험 기기</h3>

        <div class="card-box center-box">
          <div class="main-count">
            {{ dashboard.riskEquipmentCount }}건
          </div>

          <div class="sub-guide">
            클릭 시 예지보전 이동
          </div>
        </div>
      </div>

      <!-- 알림 -->
      <div class="info-card">
        <h3>실시간 알림</h3>

        <div class="card-box alert-box">
          <p v-for="(item,index) in dashboard.recentAlerts"
             :key="index">
            {{ item }}
          </p>
        </div>
      </div>

    </div>

  </section>
</template>


<script setup>

import { ref,onMounted,computed } from "vue"
import axios from "axios"
import { useRouter } from "vue-router"

const router = useRouter()

const dashboard = ref({
  todayTrafficTotal:0,
  trafficChangeRate:0,
  unprocessedCount:0,
  riskEquipmentCount:0,
  recentAlerts:[]
})

const visibleCount = ref(18)

const camImg = "/src/assets/login-bg.jpg"

const allCameras = [
  { id:1,status:"정상",image:camImg },
  { id:2,status:"정상",image:camImg },
  { id:3,status:"혼잡",image:camImg },
  { id:4,status:"정상",image:camImg },
  { id:5,status:"원활",image:camImg },
  { id:6,status:"혼잡",image:camImg },
  { id:7,status:"정상",image:camImg },
  { id:8,status:"정상",image:camImg },
  { id:9,status:"원활",image:camImg },
  { id:10,status:"정상",image:camImg },
  { id:11,status:"정상",image:camImg },
  { id:12,status:"혼잡",image:camImg },
  { id:13,status:"정상",image:camImg },
  { id:14,status:"원활",image:camImg },
  { id:15,status:"정상",image:camImg },
  { id:16,status:"정상",image:camImg },
  { id:17,status:"정상",image:camImg },
  { id:18,status:"혼잡",image:camImg }
]

const visibleCameras = computed(()=>{
  return allCameras.slice(0,visibleCount.value)
})


const loadDashboard = async ()=>{

  try{

    const res = await axios.get("http://localhost:9000/dashboard/summary")

    dashboard.value = res.data

  }catch(e){

    console.log("dashboard load error",e)

  }

}


const goViolation = ()=>{

  router.push("/main/violation")

}

const goPredict = ()=>{

  router.push("/main/predict")

}


onMounted(()=>{

  loadDashboard()

})

</script>



<style scoped>

.dashboard-page{
  width:100%;
}

.camera-grid{
  display:grid;
  grid-template-columns:repeat(6,1fr);
  gap:6px;
  margin-bottom:20px;
}

.camera-item{
  border:1px solid #ccc;
  border-radius:6px;
  overflow:hidden;
}

.camera-header{
  background:#1f2832;
  color:white;
  font-size:12px;
  padding:6px 8px;
  font-weight:700;
  display:flex;
  justify-content:space-between;
}

.camera-body{
  height:90px;
  background-size:cover;
}

.dashboard-cards{
  display:grid;
  grid-template-columns:1fr 1fr 1fr 1fr;
  gap:18px;
}

.info-card{
  background:#f4f4f4;
  border-radius:20px;
  padding:16px;
}

.card-box{
  background:white;
  border-radius:14px;
  min-height:120px;
  padding:14px;
}

.center-box{
  display:flex;
  flex-direction:column;
  justify-content:center;
  align-items:center;
}

.main-count{
  font-size:28px;
  font-weight:700;
}

.red{
  color:#d7263d;
}

.alert-box p{
  margin:0 0 8px;
}

.clickable{
  cursor:pointer;
}

</style>