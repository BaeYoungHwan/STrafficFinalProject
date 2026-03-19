<template>
  <div class="signup-page">
    <div class="signup-card" :class="{ shake: shaking }">
      <h2 class="signup-title">Sign Up</h2>

      <form @submit.prevent="handleSignup" class="signup-form" novalidate>

        <!-- ID -->
        <div class="form-group">
          <div class="input-group input-row">
            <input
              v-model="form.username"
              type="text"
              placeholder="ID"
              autocomplete="username"
              @input="resetField('username'); usernameChecked = false"
            />
            <button type="button" class="btn-check" @click="checkDuplicate" :disabled="form.username.length < 4">
              중복 확인
            </button>
          </div>
          <p v-if="errors.username" class="field-error">★ {{ errors.username }}</p>
          <p v-if="usernameOk" class="field-success">★ 사용 가능한 아이디입니다.</p>
        </div>

        <!-- PW + Confirm PW -->
        <div class="form-group">
          <div class="input-group">
            <input
              v-model="form.password"
              type="password"
              placeholder="PW"
              autocomplete="new-password"
              @input="resetField('password')"
            />
            <div class="input-separator"></div>
            <input
              v-model="form.passwordConfirm"
              type="password"
              placeholder="Confirm PW"
              autocomplete="new-password"
              @input="resetField('passwordConfirm')"
            />
          </div>
          <p class="field-hint" :class="{ 'hint-ok': pwFullyValid }">★ 영문 대/소문자, 숫자, 특수문자를 포함한 8~16자</p>
        </div>

        <!-- Name -->
        <div class="form-group">
          <div class="input-group">
            <input
              v-model="form.name"
              type="text"
              placeholder="Name"
              autocomplete="name"
              @input="resetField('name')"
            />
          </div>
          <p class="field-hint" :class="{ 'hint-ok': nameValid }">★ 필수 입력 항목입니다.</p>
        </div>

        <!-- E-mail -->
        <div class="form-group">
          <div class="input-group">
            <input
              v-model="form.email"
              type="email"
              placeholder="E-mail"
              autocomplete="email"
              @input="resetField('email')"
            />
          </div>
          <p class="field-hint" :class="{ 'hint-ok': emailValid }">★ 필수 입력 항목입니다.</p>
        </div>

        <p v-if="globalError" class="global-error">{{ globalError }}</p>

        <button type="submit" class="btn-signup" :disabled="loading">
          {{ loading ? 'Loading...' : 'Sign Up' }}
        </button>
      </form>

      <div class="signup-footer">
        <router-link to="/login" class="btn-back">Back to Login</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import api from '../api'

const router = useRouter()
const auth = useAuthStore()
const loading = ref(false)
const globalError = ref('')
const shaking = ref(false)
const usernameChecked = ref(false)
const usernameOk = ref(false)

const form = reactive({
  username: '',
  password: '',
  passwordConfirm: '',
  name: '',
  email: ''
})

const errors = reactive({
  username: '',
  password: '',
  passwordConfirm: '',
  name: '',
  email: ''
})

const pwRules = computed(() => ({
  length: form.password.length >= 8 && form.password.length <= 16,
  upper: /[A-Z]/.test(form.password),
  lower: /[a-z]/.test(form.password),
  number: /[0-9]/.test(form.password),
  special: /[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?]/.test(form.password)
}))

const allPwRulesPass = computed(() =>
  pwRules.value.length && pwRules.value.upper && pwRules.value.lower && pwRules.value.number && pwRules.value.special
)

const pwFullyValid = computed(() =>
  allPwRulesPass.value && form.password === form.passwordConfirm && form.passwordConfirm.length > 0
)

// 이름: 2자 이상, 한글 또는 영문만 허용
const nameValid = computed(() =>
  /^[가-힣a-zA-Z]{2,}$/.test(form.name.trim())
)

// 이메일: 표준 형식 (user@domain.tld)
const emailValid = computed(() =>
  /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(form.email.trim())
)

const resetField = (field) => {
  errors[field] = ''
  globalError.value = ''
}

const triggerShake = () => {
  shaking.value = true
  setTimeout(() => { shaking.value = false }, 500)
}

const checkDuplicate = async () => {
  if (form.username.length < 4) {
    errors.username = '사용 불가 아이디입니다.'
    triggerShake()
    return
  }

  try {
    const res = await api.get(`/auth/check-username?username=${encodeURIComponent(form.username)}`)
    if (res.data.exists) {
      errors.username = '이미 사용 중인 아이디입니다.'
      usernameOk.value = false
      triggerShake()
    } else {
      errors.username = ''
      usernameOk.value = true
      usernameChecked.value = true
    }
  } catch {
    errors.username = '중복확인에 실패했습니다. 다시 시도해주세요.'
    triggerShake()
  }
}

const validate = () => {
  let valid = true

  if (form.username.length < 4) {
    errors.username = '사용 불가 아이디입니다.'
    valid = false
  } else if (!usernameChecked.value) {
    errors.username = '아이디 중복확인을 해주세요.'
    valid = false
  }

  if (!allPwRulesPass.value) {
    errors.password = '비밀번호 규칙을 모두 충족해야 합니다.'
    valid = false
  }

  if (form.password !== form.passwordConfirm) {
    errors.passwordConfirm = '비밀번호가 일치하지 않습니다.'
    valid = false
  }

  if (!nameValid.value) {
    errors.name = form.name.trim().length === 0
      ? '필수 입력 항목입니다.'
      : '2자 이상 한글 또는 영문만 입력하세요.'
    valid = false
  }

  if (!emailValid.value) {
    errors.email = form.email.trim().length === 0
      ? '필수 입력 항목입니다.'
      : '올바른 이메일 형식을 입력하세요. (예: user@example.com)'
    valid = false
  }

  if (!valid) triggerShake()
  return valid
}

const handleSignup = async () => {
  globalError.value = ''
  if (!validate()) return

  loading.value = true
  try {
    await api.post('/auth/signup', {
      username: form.username,
      password: form.password,
      name: form.name,
      email: form.email
    })

    await auth.login(form.username, form.password)
    router.push('/')
  } catch (err) {
    globalError.value = err.response?.data?.message || '회원가입에 실패했습니다. 다시 시도해주세요.'
    triggerShake()
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.signup-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: #F4F6FA;
  padding: 40px 16px;
}

.signup-card {
  width: 100%;
  max-width: 380px;
  background: #FFFFFF;
  border-radius: 24px;
  padding: 36px 32px 32px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.08);
}

.signup-card.shake {
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

.signup-title {
  text-align: center;
  font-size: 24px;
  font-weight: 800;
  color: #1A1A2E;
  margin: 0 0 24px 0;
  letter-spacing: 1px;
}

.signup-form {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.input-group {
  background: #ECECEE;
  border-radius: 14px;
  overflow: hidden;
}

.input-group input {
  width: 100%;
  padding: 14px 16px;
  border: none;
  font-size: 15px;
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
  margin: 0 14px;
}

.input-row {
  display: flex;
  align-items: stretch;
}

.input-row input {
  flex: 1;
  min-width: 0;
}

.btn-check {
  padding: 0 16px;
  background: #D1D1D6;
  color: #1A1A2E;
  border: none;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: opacity 0.15s ease;
  margin: 6px 6px 6px 0;
}

.btn-check:hover:not(:disabled) {
  opacity: 0.8;
}

.btn-check:disabled {
  color: #8E8E93;
  cursor: not-allowed;
  opacity: 0.6;
}

/* 힌트 (빨간색 → 충족 시 초록) */
.field-hint {
  color: #EF4444;
  font-size: 12px;
  margin: 2px 0 0 4px;
  font-weight: 500;
}

.field-hint.hint-ok {
  color: #10B981;
}

/* 에러/성공 메시지 */
.field-error {
  color: #EF4444;
  font-size: 12px;
  margin: 2px 0 0 4px;
  font-weight: 500;
}

.field-success {
  color: #10B981;
  font-size: 12px;
  margin: 2px 0 0 4px;
  font-weight: 500;
}

.global-error {
  color: #EF4444;
  font-size: 13px;
  margin: 0;
  text-align: center;
  font-weight: 500;
}

.btn-signup {
  width: 100%;
  padding: 16px;
  background: #007AFF;
  color: #FFFFFF;
  border: none;
  border-radius: 14px;
  font-size: 17px;
  font-weight: 700;
  cursor: pointer;
  transition: opacity 0.15s ease, transform 0.1s ease;
  margin-top: 6px;
}

.btn-signup:hover:not(:disabled) {
  opacity: 0.88;
}

.btn-signup:active:not(:disabled) {
  transform: scale(0.98);
}

.btn-signup:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.signup-footer {
  text-align: center;
  margin-top: 16px;
}

.btn-back {
  color: #6B7280;
  font-size: 13px;
  text-decoration: none;
}

.btn-back:hover {
  color: #1A1A2E;
  text-decoration: underline;
}
</style>
