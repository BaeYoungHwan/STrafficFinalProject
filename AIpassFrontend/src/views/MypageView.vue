<template>
  <div class="mypage">
    <h1 class="page-title">마이페이지</h1>

    <div class="mypage-grid">
      <!-- 회원정보 카드 -->
      <div class="card profile-card" :class="{ shake: profileShaking }">
        <div class="card-header">
          <h2 class="card-title">회원정보</h2>
          <button
            v-if="!editMode"
            class="btn-edit"
            @click="editMode = true"
          >수정</button>
          <div v-else class="card-actions">
            <button class="btn-cancel" @click="cancelEdit">취소</button>
            <button class="btn-save" :disabled="profileLoading" @click="saveProfile">
              {{ profileLoading ? '저장 중...' : '저장' }}
            </button>
          </div>
        </div>

        <div class="profile-body">
          <div class="info-row">
            <span class="info-label">아이디</span>
            <span class="info-value">{{ profile.username }}</span>
          </div>

          <div class="info-row">
            <span class="info-label">이름</span>
            <template v-if="!editMode">
              <span class="info-value">{{ profile.name }}</span>
            </template>
            <template v-else>
              <div class="input-wrap">
                <input v-model="editForm.name" type="text" placeholder="이름" @input="profileError = ''" />
              </div>
            </template>
          </div>

          <div class="info-row">
            <span class="info-label">이메일</span>
            <template v-if="!editMode">
              <span class="info-value">{{ profile.email }}</span>
            </template>
            <template v-else>
              <div class="input-wrap">
                <input v-model="editForm.email" type="email" placeholder="이메일" @input="profileError = ''" />
              </div>
            </template>
          </div>

          <div class="info-row">
            <span class="info-label">가입일</span>
            <span class="info-value">{{ formatDate(profile.createdAt) }}</span>
          </div>

          <p v-if="profileError" class="msg error">{{ profileError }}</p>
          <p v-if="profileSuccess" class="msg success">{{ profileSuccess }}</p>
        </div>
      </div>

      <!-- 비밀번호 변경 카드 -->
      <div class="card pw-card" :class="{ shake: pwShaking }">
        <div class="card-header">
          <h2 class="card-title">비밀번호 변경</h2>
        </div>

        <form @submit.prevent="handleChangePassword" class="pw-form" novalidate>
          <div class="form-group">
            <label for="currentPw">현재 비밀번호</label>
            <input
              id="currentPw"
              v-model="pwForm.currentPassword"
              type="password"
              placeholder="현재 비밀번호를 입력하세요"
              autocomplete="current-password"
              @input="pwError = ''"
            />
          </div>

          <div class="form-group">
            <label for="newPw">새 비밀번호</label>
            <input
              id="newPw"
              v-model="pwForm.newPassword"
              type="password"
              placeholder="새 비밀번호 (8자 이상)"
              autocomplete="new-password"
              @input="pwError = ''"
            />
            <div class="pw-rules">
              <span :class="{ pass: pwRules.length }">8자 이상</span>
              <span :class="{ pass: pwRules.upper }">대문자</span>
              <span :class="{ pass: pwRules.lower }">소문자</span>
              <span :class="{ pass: pwRules.number }">숫자</span>
              <span :class="{ pass: pwRules.special }">특수문자</span>
            </div>
          </div>

          <div class="form-group">
            <label for="confirmPw">새 비밀번호 확인</label>
            <input
              id="confirmPw"
              v-model="pwForm.confirmPassword"
              type="password"
              placeholder="새 비밀번호를 다시 입력하세요"
              autocomplete="new-password"
              @input="pwError = ''"
            />
            <p v-if="pwForm.confirmPassword && !pwMatch" class="field-error">비밀번호가 일치하지 않습니다.</p>
            <p v-if="pwForm.confirmPassword && pwMatch" class="field-ok">비밀번호가 일치합니다.</p>
          </div>

          <p v-if="pwError" class="msg error">{{ pwError }}</p>
          <p v-if="pwSuccess" class="msg success">{{ pwSuccess }}</p>

          <button type="submit" class="btn-submit" :disabled="pwLoading">
            {{ pwLoading ? '변경 중...' : '비밀번호 변경' }}
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import api from '../api'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()

// 프로필
const profile = reactive({
  username: '',
  name: '',
  email: '',
  createdAt: ''
})
const editMode = ref(false)
const editForm = reactive({ name: '', email: '' })
const profileLoading = ref(false)
const profileError = ref('')
const profileSuccess = ref('')
const profileShaking = ref(false)

// 비밀번호
const pwForm = reactive({ currentPassword: '', newPassword: '', confirmPassword: '' })
const pwLoading = ref(false)
const pwError = ref('')
const pwSuccess = ref('')
const pwShaking = ref(false)

const pwRules = computed(() => {
  const p = pwForm.newPassword
  return {
    length: p.length >= 8,
    upper: /[A-Z]/.test(p),
    lower: /[a-z]/.test(p),
    number: /[0-9]/.test(p),
    special: /[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?]/.test(p)
  }
})

const pwMatch = computed(() => {
  return pwForm.newPassword && pwForm.newPassword === pwForm.confirmPassword
})

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

const triggerShake = (target) => {
  target.value = true
  setTimeout(() => { target.value = false }, 500)
}

const fetchProfile = async () => {
  try {
    const res = await api.get('/member/profile')
    Object.assign(profile, res.data)
  } catch {
    profileError.value = '회원정보를 불러올 수 없습니다.'
  }
}

const cancelEdit = () => {
  editMode.value = false
  profileError.value = ''
  profileSuccess.value = ''
}

const saveProfile = async () => {
  profileError.value = ''
  profileSuccess.value = ''

  if (!editForm.name.trim()) {
    profileError.value = '이름을 입력하세요.'
    triggerShake(profileShaking)
    return
  }
  if (!editForm.email || !editForm.email.includes('@')) {
    profileError.value = '올바른 이메일을 입력하세요.'
    triggerShake(profileShaking)
    return
  }

  profileLoading.value = true
  try {
    await api.put('/member/profile', {
      name: editForm.name,
      email: editForm.email
    })
    profile.name = editForm.name
    profile.email = editForm.email

    // auth store 사용자 이름도 갱신
    if (auth.user) {
      auth.user.name = editForm.name
    }

    editMode.value = false
    profileSuccess.value = '회원정보가 수정되었습니다.'
    setTimeout(() => { profileSuccess.value = '' }, 3000)
  } catch (err) {
    profileError.value = err.response?.data?.message || '수정에 실패했습니다.'
    triggerShake(profileShaking)
  } finally {
    profileLoading.value = false
  }
}

const handleChangePassword = async () => {
  pwError.value = ''
  pwSuccess.value = ''

  if (!pwForm.currentPassword) {
    pwError.value = '현재 비밀번호를 입력하세요.'
    triggerShake(pwShaking)
    return
  }
  if (!pwRules.value.length) {
    pwError.value = '새 비밀번호는 8자 이상이어야 합니다.'
    triggerShake(pwShaking)
    return
  }
  if (!pwMatch.value) {
    pwError.value = '새 비밀번호가 일치하지 않습니다.'
    triggerShake(pwShaking)
    return
  }

  pwLoading.value = true
  try {
    await api.post('/member/change-password', {
      currentPassword: pwForm.currentPassword,
      newPassword: pwForm.newPassword
    })
    pwSuccess.value = '비밀번호가 변경되었습니다.'
    pwForm.currentPassword = ''
    pwForm.newPassword = ''
    pwForm.confirmPassword = ''
    setTimeout(() => { pwSuccess.value = '' }, 3000)
  } catch (err) {
    pwError.value = err.response?.data?.message || '비밀번호 변경에 실패했습니다.'
    triggerShake(pwShaking)
  } finally {
    pwLoading.value = false
  }
}

onMounted(async () => {
  await fetchProfile()
  editForm.name = profile.name
  editForm.email = profile.email
})
</script>

<style scoped>
.mypage {
  max-width: 900px;
  margin: 0 auto;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  color: #1F3864;
  margin: 0 0 24px 0;
}

.mypage-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

.card {
  background: #ffffff;
  border-radius: 12px;
  padding: 28px;
  box-shadow: 0 2px 12px rgba(30, 56, 100, 0.06);
}

.card.shake {
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

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  padding-bottom: 14px;
  border-bottom: 1px solid #E2E8F0;
}

.card-title {
  font-size: 17px;
  font-weight: 700;
  color: #1F3864;
  margin: 0;
}

.card-actions {
  display: flex;
  gap: 8px;
}

.btn-edit {
  padding: 6px 16px;
  background: #1A6DCC;
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-edit:hover {
  background: #1457A8;
}

.btn-cancel {
  padding: 6px 16px;
  background: #f0f0f0;
  color: #666;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.btn-cancel:hover {
  background: #e0e0e0;
}

.btn-save {
  padding: 6px 16px;
  background: #10B981;
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-save:hover:not(:disabled) {
  background: #059669;
}

.btn-save:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 프로필 정보 */
.profile-body {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.info-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.info-label {
  width: 70px;
  flex-shrink: 0;
  font-size: 13px;
  font-weight: 600;
  color: #6B7280;
}

.info-value {
  font-size: 14px;
  color: #1A1A2E;
}

.input-wrap {
  flex: 1;
}

.input-wrap input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #E2E8F0;
  border-radius: 6px;
  font-size: 14px;
  color: #1d1d1f;
  background: #fafbfd;
  outline: none;
  transition: border-color 0.2s;
  box-sizing: border-box;
}

.input-wrap input:focus {
  border-color: #1A6DCC;
  background: #fff;
}

.badge-role {
  display: inline-block;
  padding: 2px 10px;
  background: #E8F1FB;
  color: #1A6DCC;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}

/* 비밀번호 폼 */
.pw-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.form-group label {
  font-size: 13px;
  font-weight: 600;
  color: #1F3864;
}

.form-group input {
  padding: 10px 14px;
  border: 1px solid #E2E8F0;
  border-radius: 6px;
  font-size: 14px;
  color: #1d1d1f;
  background: #fafbfd;
  outline: none;
  transition: border-color 0.2s;
}

.form-group input::placeholder {
  color: #bbb;
}

.form-group input:focus {
  border-color: #1A6DCC;
  background: #fff;
}

.pw-rules {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 4px;
}

.pw-rules span {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  background: #f0f0f0;
  color: #999;
  transition: all 0.2s;
}

.pw-rules span.pass {
  background: #d1fae5;
  color: #059669;
}

.field-error {
  font-size: 12px;
  color: #e74c3c;
  margin: 0;
}

.field-ok {
  font-size: 12px;
  color: #10B981;
  margin: 0;
}

.msg {
  font-size: 13px;
  text-align: center;
  margin: 4px 0 0 0;
  font-weight: 500;
}

.msg.error {
  color: #e74c3c;
}

.msg.success {
  color: #10B981;
}

.btn-submit {
  padding: 12px;
  background: #1A6DCC;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
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

@media (max-width: 768px) {
  .mypage-grid {
    grid-template-columns: 1fr;
  }
}
</style>
