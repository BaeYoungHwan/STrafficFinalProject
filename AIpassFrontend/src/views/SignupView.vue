<template>
  <div class="signup-page">
    <div class="signup-card" :class="{ shake: shaking }">
      <h2 class="signup-title">Sign Up</h2>

      <form @submit.prevent="handleSignup" class="signup-form" novalidate>

        <!-- ID -->
        <div class="form-group">
          <div class="input-row">
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
        <div class="form-group pw-group">
          <input
            v-model="form.password"
            type="password"
            placeholder="PW"
            autocomplete="new-password"
            @input="resetField('password')"
          />
          <input
            v-model="form.passwordConfirm"
            type="password"
            placeholder="Confirm PW"
            autocomplete="new-password"
            @input="resetField('passwordConfirm')"
          />
          <p class="field-hint" :class="{ 'hint-ok': pwFullyValid }">★ 영문 대/소문자, 숫자, 특수문자를 포함한 8~16자</p>
        </div>

        <!-- Name -->
        <div class="form-group">
          <input
            v-model="form.name"
            type="text"
            placeholder="Name"
            autocomplete="name"
            @input="resetField('name')"
          />
          <p class="field-hint" :class="{ 'hint-ok': nameValid }">★ 필수 입력 항목입니다.</p>
        </div>

        <!-- E-mail -->
        <div class="form-group">
          <input
            v-model="form.email"
            type="email"
            placeholder="E-mail"
            autocomplete="email"
            @input="resetField('email')"
          />
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
  max-width: 360px;
  background: #FFFFFF;
  border-radius: 16px;
  padding: 32px 28px 28px;
  box-shadow: 0 2px 16px rgba(0, 0, 0, 0.08);
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
  font-size: 20px;
  font-weight: 700;
  color: #1A1A2E;
  margin: 0 0 20px 0;
}

.signup-form {
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
  padding: 10px 14px;
  border: 1px solid #E2E8F0;
  border-radius: 8px;
  font-size: 13px;
  color: #1A1A2E;
  background: #F4F6FA;
  transition: border-color 0.2s;
  outline: none;
  width: 100%;
  box-sizing: border-box;
}

.form-group input::placeholder {
  color: #6B7280;
}

.form-group input:focus {
  border-color: #1A6DCC;
  background: #FFFFFF;
}

.input-row {
  display: flex;
  gap: 6px;
}

.input-row input {
  flex: 1;
}

.btn-check {
  padding: 0 12px;
  background: #E2E8F0;
  color: #1A1A2E;
  border: none;
  border-radius: 8px;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.2s;
}

.btn-check:hover:not(:disabled) {
  background: #cbd5e1;
}

.btn-check:disabled {
  background: #E8F1FB;
  color: #6B7280;
  cursor: not-allowed;
}

/* 항상 보이는 힌트 (빨간색 → 충족 시 초록) */
.field-hint {
  color: #EF4444;
  font-size: 11px;
  margin: 1px 0 0 2px;
  font-weight: 500;
}

.field-hint.hint-ok {
  color: #10B981;
}

/* 에러/성공 메시지 */
.field-error {
  color: #EF4444;
  font-size: 11px;
  margin: 1px 0 0 2px;
  font-weight: 500;
}

.field-success {
  color: #10B981;
  font-size: 11px;
  margin: 1px 0 0 2px;
  font-weight: 500;
}

.global-error {
  color: #EF4444;
  font-size: 12px;
  margin: 0;
  text-align: center;
  font-weight: 500;
}

.btn-signup {
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
  margin-top: 4px;
}

.btn-signup:hover:not(:disabled) {
  background: #1457A8;
}

.btn-signup:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.signup-footer {
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
