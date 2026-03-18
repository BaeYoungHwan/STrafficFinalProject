<template>
  <div class="find-page">
    <div class="find-card" :class="{ shake: shaking }">

      <!-- Step 1: Find ID/PW 선택 -->
      <template v-if="step === 'select'">
        <h2 class="find-title">Find ID/PW</h2>
        <div class="select-buttons">
          <button class="btn-select" @click="step = 'findId'">Find ID</button>
          <button class="btn-select" @click="step = 'resetPw'">Reset PW</button>
        </div>
        <div class="find-footer">
          <router-link to="/login" class="btn-back">Back to Login</router-link>
        </div>
      </template>

      <!-- Step 2a: Find ID -->
      <template v-if="step === 'findId'">
        <h2 class="find-title">Find ID</h2>
        <form @submit.prevent="handleFindId" class="find-form" novalidate>
          <div class="form-group">
            <input v-model="idForm.name" type="text" placeholder="Name" @input="idErrors.name = ''" />
            <p v-if="idErrors.name" class="field-error">★ {{ idErrors.name }}</p>
          </div>
          <div class="form-group">
            <input v-model="idForm.email" type="email" placeholder="E-mail" @input="idErrors.email = ''" />
            <p v-if="idErrors.email" class="field-error">★ {{ idErrors.email }}</p>
          </div>
          <p v-if="idError" class="global-error">{{ idError }}</p>
          <button type="submit" class="btn-submit" :disabled="idLoading">
            {{ idLoading ? 'Loading...' : 'Find ID' }}
          </button>
        </form>
        <div class="find-footer">
          <router-link to="/login" class="btn-back">Back to Login</router-link>
        </div>
      </template>

      <!-- Step 2b: Find ID 결과 -->
      <template v-if="step === 'idResult'">
        <h2 class="find-title">Find ID</h2>
        <div class="result-box">
          <div class="result-row">
            <span class="result-label">Name :</span>
            <span class="result-value">{{ foundName }}</span>
          </div>
          <div class="result-row">
            <span class="result-label">E-Mail :</span>
            <span class="result-value">{{ foundEmail }}</span>
          </div>
          <div class="result-row">
            <span class="result-label">ID :</span>
            <span class="result-value highlight">{{ foundUsername }}</span>
          </div>
        </div>
        <button class="btn-submit" @click="step = 'resetPw'">Find PW</button>
        <div class="find-footer">
          <router-link to="/login" class="btn-back">Back to Login</router-link>
        </div>
      </template>

      <!-- Step 3a: Reset PW 본인 확인 -->
      <template v-if="step === 'resetPw'">
        <h2 class="find-title">Reset PW</h2>
        <form @submit.prevent="handleVerifyForReset" class="find-form" novalidate>
          <div class="form-group">
            <input v-model="pwForm.username" type="text" placeholder="ID" @input="pwErrors.username = ''" />
            <p v-if="pwErrors.username" class="field-error">★ {{ pwErrors.username }}</p>
          </div>
          <div class="form-group">
            <input v-model="pwForm.email" type="email" placeholder="E-mail" @input="pwErrors.email = ''" />
            <p v-if="pwErrors.email" class="field-error">★ {{ pwErrors.email }}</p>
          </div>
          <p v-if="pwError" class="global-error">{{ pwError }}</p>
          <button type="submit" class="btn-submit" :disabled="pwLoading">
            {{ pwLoading ? 'Loading...' : 'Reset Password' }}
          </button>
        </form>
        <div class="find-footer">
          <router-link to="/login" class="btn-back">Back to Login</router-link>
        </div>
      </template>

      <!-- Step 3b: Reset Password 새 비밀번호 -->
      <template v-if="step === 'newPassword'">
        <h2 class="find-title">Reset Password</h2>
        <form @submit.prevent="handleResetPassword" class="find-form" novalidate>
          <div class="form-group">
            <input v-model="newPwForm.password" type="password" placeholder="PW" @input="newPwErrors.password = ''" />
          </div>
          <div class="form-group">
            <input v-model="newPwForm.confirmPassword" type="password" placeholder="Confirm PW" @input="newPwErrors.confirmPassword = ''" />
            <p class="field-hint" :class="{ 'hint-ok': allNewPwRulesPass }">★ 영문 대/소문자, 숫자, 특수문자를 포함한 8~16자</p>
            <p v-if="newPwForm.confirmPassword && newPwForm.password !== newPwForm.confirmPassword" class="field-error">★ 비밀번호가 일치하지 않습니다.</p>
          </div>
          <p v-if="newPwError" class="global-error">{{ newPwError }}</p>
          <button type="submit" class="btn-submit" :disabled="newPwLoading">
            {{ newPwLoading ? 'Loading...' : 'Reset Password' }}
          </button>
        </form>
        <div class="find-footer">
          <router-link to="/login" class="btn-back">Back to Login</router-link>
        </div>
      </template>

    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api'

const router = useRouter()
const step = ref('select')
const shaking = ref(false)

const triggerShake = () => {
  shaking.value = true
  setTimeout(() => { shaking.value = false }, 500)
}

// ── Find ID ──
const idForm = reactive({ name: '', email: '' })
const idErrors = reactive({ name: '', email: '' })
const idError = ref('')
const idLoading = ref(false)
const foundUsername = ref('')
const foundName = ref('')
const foundEmail = ref('')

const handleFindId = async () => {
  let valid = true
  idError.value = ''

  if (!/^[가-힣a-zA-Z]{2,}$/.test(idForm.name.trim())) {
    idErrors.name = idForm.name.trim().length === 0 ? '이름을 입력하세요.' : '2자 이상 한글 또는 영문만 입력하세요.'
    valid = false
  }
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(idForm.email.trim())) {
    idErrors.email = idForm.email.trim().length === 0 ? '이메일을 입력하세요.' : '올바른 이메일 형식을 입력하세요.'
    valid = false
  }
  if (!valid) { triggerShake(); return }

  idLoading.value = true
  try {
    const res = await api.post('/auth/find-id', { name: idForm.name, email: idForm.email })
    foundUsername.value = res.data.username
    foundName.value = idForm.name
    foundEmail.value = idForm.email
    step.value = 'idResult'
  } catch (err) {
    idError.value = err.response?.data?.message || '일치하는 계정을 찾을 수 없습니다.'
    triggerShake()
  } finally {
    idLoading.value = false
  }
}

// ── Reset PW (본인 확인) ──
const pwForm = reactive({ username: '', email: '' })
const pwErrors = reactive({ username: '', email: '' })
const pwError = ref('')
const pwLoading = ref(false)

const handleVerifyForReset = async () => {
  let valid = true
  pwError.value = ''

  if (!pwForm.username.trim()) { pwErrors.username = '아이디를 입력하세요.'; valid = false }
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(pwForm.email.trim())) {
    pwErrors.email = pwForm.email.trim().length === 0 ? '이메일을 입력하세요.' : '올바른 이메일 형식을 입력하세요.'
    valid = false
  }
  if (!valid) { triggerShake(); return }

  pwLoading.value = true
  try {
    await api.post('/auth/verify-reset', { username: pwForm.username, email: pwForm.email })
    step.value = 'newPassword'
  } catch (err) {
    pwError.value = err.response?.data?.message || '일치하는 계정을 찾을 수 없습니다.'
    triggerShake()
  } finally {
    pwLoading.value = false
  }
}

// ── Reset Password (새 비밀번호) ──
const newPwForm = reactive({ password: '', confirmPassword: '' })
const newPwErrors = reactive({ password: '', confirmPassword: '' })
const newPwError = ref('')
const newPwLoading = ref(false)

const newPwRules = computed(() => ({
  length: newPwForm.password.length >= 8 && newPwForm.password.length <= 16,
  upper: /[A-Z]/.test(newPwForm.password),
  lower: /[a-z]/.test(newPwForm.password),
  number: /[0-9]/.test(newPwForm.password),
  special: /[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?]/.test(newPwForm.password)
}))

const allNewPwRulesPass = computed(() =>
  newPwRules.value.length && newPwRules.value.upper && newPwRules.value.lower && newPwRules.value.number && newPwRules.value.special
  && newPwForm.password === newPwForm.confirmPassword && newPwForm.confirmPassword.length > 0
)

const handleResetPassword = async () => {
  let valid = true
  newPwError.value = ''

  if (!allNewPwRulesPass.value) {
    newPwErrors.password = '비밀번호 규칙을 모두 충족해야 합니다.'
    valid = false
  }
  if (newPwForm.password !== newPwForm.confirmPassword) {
    newPwErrors.confirmPassword = '비밀번호가 일치하지 않습니다.'
    valid = false
  }
  if (!valid) { triggerShake(); return }

  newPwLoading.value = true
  try {
    await api.post('/auth/reset-password', {
      username: pwForm.username,
      email: pwForm.email,
      newPassword: newPwForm.password
    })
    router.push('/login')
  } catch (err) {
    newPwError.value = err.response?.data?.message || '비밀번호 재설정에 실패했습니다.'
    triggerShake()
  } finally {
    newPwLoading.value = false
  }
}
</script>

<style scoped>
.find-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: #F4F6FA;
  padding: 40px 16px;
}

.find-card {
  width: 100%;
  max-width: 360px;
  background: #FFFFFF;
  border-radius: 16px;
  padding: 32px 28px 28px;
  box-shadow: 0 2px 16px rgba(0, 0, 0, 0.08);
}

.find-card.shake {
  animation: shake 0.45s ease-in-out;
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  15% { transform: translateX(-8px); }
  30% { transform: translateX(7px); }
  45% { transform: translateX(-6px); }
  60% { transform: translateX(5px); }
  75% { transform: translateX(-3px); }
  90% { transform: translateX(2px); }
}

.find-title {
  text-align: center;
  font-size: 20px;
  font-weight: 700;
  color: #1A1A2E;
  margin: 0 0 20px 0;
}

.select-buttons {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 16px;
}

.btn-select {
  width: 100%;
  padding: 12px;
  background: #1A6DCC;
  color: #FFFFFF;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-select:hover {
  background: #1457A8;
}

.find-form {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.form-group input {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid #E2E8F0;
  border-radius: 8px;
  font-size: 13px;
  color: #1A1A2E;
  background: #F4F6FA;
  transition: border-color 0.2s;
  outline: none;
  box-sizing: border-box;
}

.form-group input::placeholder {
  color: #6B7280;
}

.form-group input:focus {
  border-color: #1A6DCC;
  background: #FFFFFF;
}

.field-error {
  color: #EF4444;
  font-size: 11px;
  margin: 1px 0 0 2px;
  font-weight: 500;
}

.field-hint {
  color: #EF4444;
  font-size: 11px;
  margin: 1px 0 0 2px;
  font-weight: 500;
}

.field-hint.hint-ok {
  color: #10B981;
}

.global-error {
  color: #EF4444;
  font-size: 12px;
  margin: 0;
  text-align: center;
  font-weight: 500;
}

.result-box {
  background: #E8F1FB;
  border: 1px solid #E2E8F0;
  border-radius: 10px;
  padding: 18px 20px;
  margin-bottom: 12px;
}

.result-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
}

.result-label {
  font-size: 13px;
  font-weight: 600;
  color: #6B7280;
  min-width: 60px;
}

.result-value {
  font-size: 13px;
  color: #1A1A2E;
  font-weight: 500;
}

.result-value.highlight {
  font-weight: 700;
  color: #1A6DCC;
  font-size: 15px;
}

.btn-submit {
  width: 100%;
  padding: 12px;
  background: #1A6DCC;
  color: #FFFFFF;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-submit:hover:not(:disabled) {
  background: #1457A8;
}

.btn-submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.find-footer {
  text-align: center;
  margin-top: 12px;
}

.btn-back {
  color: #6B7280;
  font-size: 12px;
  text-decoration: none;
}

.btn-back:hover {
  color: #1A6DCC;
  text-decoration: underline;
}
</style>
