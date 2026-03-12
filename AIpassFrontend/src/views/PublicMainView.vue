<template>
  <div class="public-page">
    <header class="top-header">
      <div class="brand-wrap">
        <h1 class="brand" @click="goMenu('/main/dashboard')">AI - Pass</h1>
      </div>

      <div class="user-actions">
        <button class="text-btn" @click="logout">LOGOUT</button>
        <button class="mypage-btn" @click="goMypage">MYPAGE</button>
      </div>
    </header>

    <nav class="gnb-wrap">
      <ul class="gnb-list">
        <li
          v-for="menu in menus"
          :key="menu.label"
          class="gnb-item"
          :class="getMenuClass(menu.path)"
          @click="goMenu(menu.path)"
        >
          {{ menu.label }}
        </li>
      </ul>

      <button class="arrow-btn">›</button>
    </nav>

    <main class="content-area">
      <router-view />
    </main>

    <footer class="footer-card">
      <div class="footer-inner">
        <p class="members">BAE YOUNGWHAN | KIM SOYEON | HA JAEYOUNG | OH JONGSEOK</p>

        <div class="logo-row">
          <img :src="kdigital" alt="K-Digital Training" class="logo-img kdigital-logo" />
          <img :src="its" alt="ITS Korea" class="logo-img its-logo" />
          <img :src="mbc" alt="MBC 컴퓨터교육센터" class="logo-img mbc-logo" />
          <img :src="straffic" alt="sTraffic" class="logo-img straffic-logo" />
        </div>

        <h2 class="footer-brand">AI - Pass</h2>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { useRouter, useRoute } from 'vue-router'
import kdigital from '../assets/logo/kdigital.png'
import its from '../assets/logo/its.png'
import mbc from '../assets/logo/mbc.png'
import straffic from '../assets/logo/straffic.png'

const router = useRouter()
const route = useRoute()

const menus = [
  { label: '메인', path: '/main/dashboard' },
  { label: '교통/신호 제어', path: '/main/traffic' },
  { label: 'CCTV', path: '/main/cctv' },
  { label: '단속 내역', path: '/main/violation' },
  { label: '설비 예지보전', path: '/main/predict' },
  { label: '통계', path: '/main/stats' },
]

const goMenu = (path) => {
  router.push(path)
}

const logout = () => {
  router.push('/')
}

const goMypage = () => {
  alert('마이페이지는 아직 연결되지 않았습니다.')
}

const getMenuClass = (path) => {
  if (route.path === path && path === '/main/dashboard') {
    return 'active-main'
  }
  if (route.path === path) {
    return 'active'
  }
  return ''
}
</script>

<style scoped>
* {
  box-sizing: border-box;
}

.public-page {
  width: 100%;
  min-height: 100vh;
  padding: 20px 20px 18px;
  background: #f3f3f3;
  color: #1d1d1f;
  font-family: 'Pretendard', 'Noto Sans KR', sans-serif;
}

.top-header {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 18px;
}

.brand-wrap {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
}

.brand {
  margin: 0;
  font-size: 42px;
  font-weight: 800;
  letter-spacing: -1px;
  line-height: 1;
  color: #111;
  cursor: pointer;
}

.user-actions {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 14px;
  min-width: 250px;
}

.text-btn {
  height: 44px;
  padding: 0 8px;
  border: none;
  background: transparent;
  font-size: 18px;
  font-weight: 500;
  color: #111;
  cursor: pointer;
  white-space: nowrap;
}

.mypage-btn {
  width: 120px;
  height: 48px;
  border: none;
  border-radius: 14px;
  background: #1389ff;
  color: white;
  font-size: 18px;
  font-weight: 700;
  cursor: pointer;
  white-space: nowrap;
  box-shadow: 0 8px 16px rgba(19, 137, 255, 0.16);
}

.gnb-wrap {
  width: 100%;
  margin: 0 0 20px;
  padding: 10px 14px 10px 18px;
  display: flex;
  align-items: center;
  gap: 10px;
  background: rgba(255, 255, 255, 0.9);
  border-radius: 999px;
  box-shadow: 0 8px 18px rgba(0, 0, 0, 0.08);
  overflow: hidden;
}

.gnb-list {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0;
  list-style: none;
  padding: 0;
  margin: 0;
  overflow-x: auto;
  overflow-y: hidden;
  white-space: nowrap;
  scrollbar-width: none;
}

.gnb-list::-webkit-scrollbar {
  display: none;
}

.gnb-item {
  position: relative;
  flex: 0 0 auto;
  padding: 8px 18px;
  font-size: 18px;
  font-weight: 500;
  color: #222;
  cursor: pointer;
  white-space: nowrap;
  line-height: 1.2;
}

.gnb-item + .gnb-item::before {
  content: '|';
  position: absolute;
  left: -2px;
  top: 50%;
  transform: translateY(-50%);
  color: #b9b9b9;
}

.gnb-item.active {
  font-weight: 700;
  color: #1389ff;
}

.gnb-item.active-main {
  font-weight: 700;
  color: #ff383c;
}

.arrow-btn {
  flex: 0 0 auto;
  width: 38px;
  height: 38px;
  border: none;
  border-radius: 50%;
  background: #f1f1f1;
  color: #333;
  font-size: 24px;
  line-height: 1;
  cursor: pointer;
}

.content-area {
  width: 100%;
}

.footer-card {
  width: 100%;
  margin-top: 18px;
  padding-top: 12px;
  border-top: 4px solid #dcdcdc;
}

.footer-inner {
  background: #efefef;
  border-radius: 28px;
  padding: 22px 20px 18px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.65), 0 10px 22px rgba(0, 0, 0, 0.05);
}

.members {
  text-align: center;
  font-size: 17px;
  font-weight: 500;
  color: #666e79;
  margin: 0 0 16px;
}

.logo-row {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 22px;
  flex-wrap: wrap;
  margin-bottom: 14px;
}

.logo-img {
  object-fit: contain;
  display: block;
}

.kdigital-logo {
  height: 28px;
}

.its-logo {
  height: 30px;
}

.mbc-logo {
  height: 32px;
}

.straffic-logo {
  height: 28px;
}

.footer-brand {
  margin: 0;
  text-align: center;
  font-size: 30px;
  font-weight: 800;
  color: #111;
}

@media (max-width: 1200px) {
  .public-page {
    padding: 16px 14px;
  }

  .top-header {
    gap: 16px;
    margin-bottom: 14px;
  }

  .brand {
    font-size: 34px;
  }

  .user-actions {
    min-width: auto;
    gap: 10px;
  }

  .text-btn {
    font-size: 16px;
    height: 40px;
  }

  .mypage-btn {
    width: 108px;
    height: 42px;
    font-size: 16px;
  }

  .gnb-wrap {
    padding: 8px 10px 8px 14px;
    margin-bottom: 16px;
  }

  .gnb-item {
    font-size: 16px;
    padding: 8px 14px;
  }

  .arrow-btn {
    width: 34px;
    height: 34px;
    font-size: 22px;
  }

  .members {
    font-size: 15px;
  }

  .logo-row {
    gap: 16px;
  }

  .kdigital-logo,
  .its-logo,
  .mbc-logo,
  .straffic-logo {
    height: 24px;
  }

  .footer-brand {
    font-size: 26px;
  }
}

@media (max-width: 768px) {
  .top-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .user-actions {
    width: 100%;
    justify-content: flex-start;
  }

  .brand {
    font-size: 30px;
  }

  .gnb-wrap {
    border-radius: 20px;
  }
}
</style>