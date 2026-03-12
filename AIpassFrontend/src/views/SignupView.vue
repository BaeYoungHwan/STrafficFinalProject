<template>
  <div class="signup-page" :style="signupPageStyle">
    <div class="signup-box">
      <h2 class="signup-title">SIGN UP</h2>

      <input
        v-model="name"
        type="text"
        placeholder="NAME"
        class="signup-input"
        @keyup.enter="signup"
      />

      <input
        v-model="loginId"
        type="text"
        placeholder="ID"
        class="signup-input"
        @keyup.enter="signup"
      />

      <input
        v-model="password"
        type="password"
        placeholder="PW"
        class="signup-input"
        @keyup.enter="signup"
      />

      <button class="signup-main-btn" @click="signup">SIGN UP</button>

      <button class="back-btn" @click="goLogin">Back To Login</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import loginBg from '../assets/login-bg.jpg'

const router = useRouter()

const name = ref('')
const loginId = ref('')
const password = ref('')

const signupPageStyle = computed(() => ({
  backgroundImage: `linear-gradient(rgba(255,255,255,0.35), rgba(255,255,255,0.35)), url(${loginBg})`,
}))

const signup = async () => {
  if (!name.value || !loginId.value || !password.value) {
    alert('이름, 아이디, 비밀번호를 모두 입력해주세요.')
    return
  }

  try {
    const response = await fetch('http://localhost:9000/auth/signup', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        name: name.value,
        loginId: loginId.value,
        password: password.value,
      }),
    })

    if (!response.ok) {
      alert('서버 요청에 실패했습니다.')
      return
    }

    const data = await response.json()

    if (data === true) {
      alert('회원가입 성공')
      router.push('/')
    } else {
      alert('이미 존재하는 아이디입니다.')
    }
  } catch (error) {
    console.error(error)
    alert('서버 연결에 실패했습니다.')
  }
}

const goLogin = () => {
  router.push('/')
}
</script>

<style scoped>
.signup-page {
  width: 100%;
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
}

.signup-box {
  width: 380px;
  padding: 40px 30px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.88);
  backdrop-filter: blur(6px);
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.18);
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.signup-title {
  text-align: center;
  font-size: 28px;
  font-weight: 700;
  margin: 0 0 10px 0;
  color: #111;
}

.signup-input {
  width: 100%;
  height: 52px;
  border: none;
  border-radius: 14px;
  padding: 0 16px;
  background: #ececec;
  font-size: 16px;
  outline: none;
}

.signup-main-btn {
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

.back-btn {
  width: 100%;
  height: 48px;
  border: none;
  border-radius: 14px;
  background: #dcdcdc;
  color: #111;
  font-size: 16px;
  cursor: pointer;
}
</style>