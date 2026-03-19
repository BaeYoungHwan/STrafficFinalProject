<template>
  <header class="app-header">
    <div class="header-left">
      <router-link to="/" class="logo">
        <svg class="logo-icon" xmlns="http://www.w3.org/2000/svg" width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="" y1="12" x2="22" y2="12" /><line x1="12" y1="2" x2="12" y2="22" />
          <path d="M20 16c-4 0-6-2-6-6s2-6 6-6" /><path d="M4 8c4 0 6 2 6 6s-2 6-6 6" />
        </svg>
        <span class="logo-text">AI-Pass</span>
      </router-link>
    </div>
    <div class="header-right">
      <button class="btn-logout" @click="handleLogout">LOGOUT</button>
      <router-link to="/mypage" class="btn-mypage">MYPAGE</router-link>
    </div>
  </header>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()

const handleLogout = async () => {
  await auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 40px;
  height: 50px;
  background: #FFFFFF;
}

.header-left .logo {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  color: #1A1A2E;
}

.logo-icon {
  color: #1A6DCC;
  width: 24px;
  height: 24px;
}

.logo-text {
  font-size: 22px;
  font-weight: 800;
  color: #1A1A2E;
}

.header-right {
  display: flex;
  gap: 20px;
}

.btn-logout {
  background: none;
  border: none;
  color: #000000;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  padding: 8px 12px;
  letter-spacing: 0.5px;
}

.btn-logout:hover {
  color: #1A1A2E;
}

.btn-mypage {
  background: #1A6DCC;
  color: #ffffff;
  border: none;
  border-radius: 10px;
  padding: 10px 22px;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  text-decoration: none;
  letter-spacing: 0.5px;
}

.btn-mypage:hover {
  background: #1457A8;
}
</style>
