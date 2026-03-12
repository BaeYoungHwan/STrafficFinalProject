<template>
  <div class="login-page" :style="loginPageStyle">
    <div class="login-box">
      <h2 class="login-title">LOGIN</h2>

      <input
        v-model="loginId"
        type="text"
        placeholder="ID"
        class="login-input"
        @keyup.enter="login"
      />

      <input
        v-model="password"
        type="password"
        placeholder="PW"
        class="login-input"
        @keyup.enter="login"
      />

      <button class="login-btn" @click="login">LOGIN</button>

      <button class="signup-btn" @click="goSignup">Sign Up</button>

      <button class="find-btn" @click="showFindIdMessage">Forgot ID?</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import loginBg from '../assets/login-bg.jpg'

const router = useRouter()

const loginId = ref('')
const password = ref('')

const loginPageStyle = computed(() => ({
  backgroundImage: `linear-gradient(rgba(255,255,255,0.35), rgba(255,255,255,0.35)), url(${loginBg})`,
}))

const login = async () => {
  if (!loginId.value || !password.value) {
    alert('아이디와 비밀번호를 입력해주세요.')
    return
  }

  try {
    const response = await fetch('http://localhost:9000/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        loginId: loginId.value,
        password: password.value,
      }),
    })

    if (!response.ok) {
      alert('서버 요청에 실패했습니다.')
      return
    }

    const data = await response.json()

    if (data && data.loginId) {
      alert('로그인 성공')
      router.push('/main')
    } else {
      alert('아이디 또는 비밀번호가 틀렸습니다.')
    }
  } catch (error) {
    console.error(error)
    alert('서버 연결에 실패했습니다.')
  }
}

const goSignup = () => {
  router.push('/signup')
}

const showFindIdMessage = () => {
  alert('아이디 찾기 기능은 아직 연결되지 않았습니다.')
}
</script>

<style scoped>
.login-page {
  width: 100%;
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
}

.login-box {
  width: 360px;
  padding: 40px 30px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.88);
  backdrop-filter: blur(6px);
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.18);
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.login-title {
  text-align: center;
  font-size: 28px;
  font-weight: 700;
  margin: 0 0 10px 0;
  color: #111;
}

.login-input {
  width: 100%;
  height: 52px;
  border: none;
  border-radius: 14px;
  padding: 0 16px;
  background: #ececec;
  font-size: 16px;
  outline: none;
}

.login-btn {
  width: 100%;
  height: 52px;
  border: none;
  border-radius: 14px;
  background: #1e88e5;
  color: white;
  font-size: 18px;
  font-weight: 700;
  cursor: pointer;
}

.signup-btn {
  width: 100%;
  height: 48px;
  border: none;
  border-radius: 14px;
  background: #dcdcdc;
  color: #111;
  font-size: 16px;
  cursor: pointer;
}

.find-btn {
  border: none;
  background: none;
  color: red;
  font-size: 14px;
  cursor: pointer;
}
</style>