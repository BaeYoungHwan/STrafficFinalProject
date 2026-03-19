<template>
  <div class="login-page">
    <div class="login-card">
      <h2 class="login-title">LOGIN</h2>

      <form @submit.prevent="handleLogin" class="login-form" novalidate>
        <div class="input-group">
          <input
            id="username"
            v-model="form.username"
            type="text"
            placeholder="ID"
            required
            autocomplete="username"
          />
          <div class="input-separator"></div>
          <input
            id="password"
            v-model="form.password"
            type="password"
            placeholder="PW"
            required
            autocomplete="current-password"
          />
        </div>

        <p v-if="errorMsg" class="error-msg">{{ errorMsg }}</p>

        <button type="submit" class="btn-login" :disabled="loading">
          {{ loading ? 'Loading...' : 'LOGIN' }}
        </button>
      </form>

      <button class="btn-signup" @click="$router.push('/signup')">Sign Up</button>

      <router-link to="/find-account" class="link-forgot">Forgot ID?</router-link>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()
const loading = ref(false)
const errorMsg = ref('')

const form = reactive({
  username: '',
  password: ''
})

const handleLogin = async () => {
  loading.value = true
  errorMsg.value = ''

  if (!form.username.trim() || !form.password) {
    errorMsg.value = '아이디와 비밀번호를 입력하세요.'
    loading.value = false
    return
  }

  try {
    await auth.login(form.username, form.password)
    router.push('/')
  } catch (err) {
    errorMsg.value = err.response?.data?.message || '로그인에 실패했습니다. 아이디와 비밀번호를 확인하세요.'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: #F4F6FA;
}

.login-card {
  width: 100%;
  max-width: 380px;
  background: #FFFFFF;
  border-radius: 24px;
  padding: 44px 32px 36px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.08);
  text-align: center;
}

.login-title {
  font-size: 26px;
  font-weight: 800;
  color: #1A1A2E;
  margin: 0 0 28px 0;
  letter-spacing: 2px;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.input-group {
  background: #ECECEE;
  border-radius: 14px;
  overflow: hidden;
}

.input-group input {
  width: 100%;
  padding: 16px 18px;
  border: none;
  font-size: 16px;
  color: #1A1A2E;
  background: transparent;
  outline: none;
  box-sizing: border-box;
}

.input-group input::placeholder {
  color: #8E8E93;
  font-weight: 500;
}

.input-separator {
  height: 1px;
  background: #D1D1D6;
  margin: 0 16px;
}

.error-msg {
  color: #EF4444;
  font-size: 13px;
  margin: 2px 0 0 0;
  text-align: center;
}

.btn-login {
  width: 100%;
  padding: 16px;
  background: #007AFF;
  color: #ffffff;
  border: none;
  border-radius: 14px;
  font-size: 17px;
  font-weight: 700;
  cursor: pointer;
  transition: opacity 0.15s ease, transform 0.1s ease;
  letter-spacing: 1px;
}

.btn-login:hover:not(:disabled) {
  opacity: 0.88;
}

.btn-login:active:not(:disabled) {
  transform: scale(0.98);
}

.btn-login:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-signup {
  width: 100%;
  padding: 16px;
  background: #E5E5EA;
  color: #1A1A2E;
  border: none;
  border-radius: 14px;
  font-size: 17px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.15s ease, transform 0.1s ease;
  margin-top: 10px;
}

.btn-signup:hover {
  opacity: 0.88;
}

.btn-signup:active {
  transform: scale(0.98);
}

.link-forgot {
  display: inline-block;
  margin-top: 16px;
  color: #EF4444;
  font-size: 14px;
  font-weight: 500;
  text-decoration: none;
}

.link-forgot:hover {
  text-decoration: underline;
}
</style>
