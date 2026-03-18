<template>
  <div class="login-page">
    <div class="login-card">
      <h2 class="login-title">LOGIN</h2>

      <form @submit.prevent="handleLogin" class="login-form" novalidate>
        <div class="form-group">
          <input
            id="username"
            v-model="form.username"
            type="text"
            placeholder="ID"
            required
            autocomplete="username"
          />
        </div>
        <div class="form-group">
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
  max-width: 360px;
  background: #FFFFFF;
  border-radius: 16px;
  padding: 40px 28px 32px;
  box-shadow: 0 2px 16px rgba(0, 0, 0, 0.08);
  text-align: center;
}

.login-title {
  font-size: 24px;
  font-weight: 800;
  color: #1A1A2E;
  margin: 0 0 32px 0;
  letter-spacing: 2px;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.form-group input {
  width: 100%;
  padding: 14px 18px;
  border: 1px solid #E2E8F0;
  border-radius: 10px;
  font-size: 14px;
  color: #1A1A2E;
  background: #F4F6FA;
  transition: border-color 0.2s, background 0.2s;
  outline: none;
  box-sizing: border-box;
}

.form-group input::placeholder {
  color: #6B7280;
  font-weight: 500;
}

.form-group input:focus {
  border-color: #1A6DCC;
  background: #FFFFFF;
}

.error-msg {
  color: #EF4444;
  font-size: 13px;
  margin: 4px 0 0 0;
  text-align: center;
}

.btn-login {
  width: 100%;
  padding: 14px;
  background: #1A6DCC;
  color: #ffffff;
  border: none;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.2s;
  letter-spacing: 2px;
  margin-top: 8px;
}

.btn-login:hover:not(:disabled) {
  background: #1457A8;
}

.btn-login:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-signup {
  width: 100%;
  padding: 14px;
  background: #E2E8F0;
  color: #1A1A2E;
  border: none;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
  margin-top: 10px;
}

.btn-signup:hover {
  background: #cbd5e1;
}

.link-forgot {
  display: inline-block;
  margin-top: 16px;
  color: #EF4444;
  font-size: 13px;
  font-weight: 500;
  text-decoration: none;
}

.link-forgot:hover {
  text-decoration: underline;
}
</style>
