<template>
  <header class="app-header">
    <div class="header-left">
      <router-link to="/" class="logo">
        <img :src="aipassLogo" alt="AI-PASS" class="logo-img" />
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
import aipassLogo from '../assets/logos/AI-PASS_LOGO.png'

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

.logo-img {
  height: 36px;
  object-fit: contain;
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
