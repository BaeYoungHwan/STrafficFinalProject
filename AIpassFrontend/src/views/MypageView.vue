<template>
  <div class="mypage">
    <h1 class="page-title">MY PAGE</h1>

    <div class="cards-wrap" :class="{ 'dual-mode': editMode }">
      <!-- 왼쪽: 회원정보 (읽기 전용) -->
      <div class="card view-card" :class="{ shake: profileShaking }">
        <div class="card-header-center">
          <h2 class="card-title">회원정보</h2>
        </div>

        <div class="profile-body">
          <div class="info-row">
            <span class="info-label">아이디</span>
            <span class="info-value">{{ profile.username }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">이름</span>
            <span class="info-value">{{ profile.name }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">이메일</span>
            <span class="info-value">{{ profile.email }}</span>
          </div>
          <div class="info-row last">
            <span class="info-label">가입일</span>
            <span class="info-value">{{ formatDate(profile.createdAt) }}</span>
          </div>
        </div>

        <div class="card-footer">
          <button
            class="btn-primary-pill"
            :class="{ 'btn-disabled': editMode }"
            :disabled="editMode"
            @click="enterEditMode"
          >수정</button>
        </div>

        <p v-if="profileSuccess && !editMode" class="msg success">{{ profileSuccess }}</p>
      </div>

      <!-- 오른쪽: 회원정보 수정 (수정 모드에서만 표시) -->
      <div v-if="editMode" class="card edit-card">
        <div class="card-header-center">
          <h2 class="card-title">회원정보 수정</h2>
        </div>

        <div class="profile-body">
          <div class="info-row">
            <span class="info-label">아이디</span>
            <span class="info-value readonly">{{ profile.username }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">이름</span>
            <span class="info-value readonly">{{ profile.name }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">이메일</span>
            <div class="email-input-wrap">
              <div class="email-field">
                <input
                  ref="emailLocalRef"
                  v-model="emailLocal"
                  type="text"
                  placeholder="이메일"
                  @input="onEmailInput"
                  @focus="showDomainDropdown = true"
                />
                <span class="at-sign">@</span>
                <div class="domain-select-wrap">
                  <input
                    v-model="emailDomain"
                    type="text"
                    placeholder="직접입력"
                    :readonly="emailDomainSelected !== '직접입력'"
                    @focus="showDomainDropdown = true"
                  />
                  <button
                    class="domain-toggle"
                    type="button"
                    @click="showDomainDropdown = !showDomainDropdown"
                  >&#9662;</button>
                  <ul v-if="showDomainDropdown" class="domain-dropdown">
                    <li
                      v-for="d in domainOptions"
                      :key="d"
                      :class="{ active: emailDomainSelected === d }"
                      @mousedown.prevent="selectDomain(d)"
                    >{{ d }}</li>
                  </ul>
                </div>
                <button
                  v-if="emailLocal || emailDomain"
                  class="btn-clear-email"
                  type="button"
                  @click="clearEmail"
                >&times;</button>
              </div>
            </div>
            <button
              v-if="!emailCodeSent || emailVerified"
              class="btn-verify-send btn-verify-inline"
              :class="{ 'btn-verified': emailVerified }"
              :disabled="emailSending || emailVerified"
              @click="sendEmailCode"
            >{{ emailVerified ? '인증완료' : emailSending ? '전송 중...' : '인증요청' }}</button>
          </div>
          <!-- 이메일 인증 pill (인증 요청 후 ~ 인증 완료 전) -->
          <div v-if="emailCodeSent && !emailVerified" class="info-row verify-row">
            <span class="info-label">이메일 인증</span>
            <div class="email-verify-wrap">
              <input
                v-model="emailVerifyCode"
                type="text"
                class="verify-code-input"
                placeholder="인증코드 6자리"
                maxlength="6"
              />
              <button
                class="btn-verify-check"
                :disabled="emailVerifying"
                @click="checkEmailCode"
              >{{ emailVerifying ? '확인 중...' : '확인' }}</button>
              <button
                class="btn-verify-resend"
                :disabled="emailSending"
                @click="sendEmailCode"
              >재전송</button>
            </div>
          </div>
          <p v-if="emailVerifyError" class="field-error verify-error-msg">{{ emailVerifyError }}</p>
          <div class="info-row last">
            <span class="info-label">가입일</span>
            <span class="info-value readonly">{{ formatDate(profile.createdAt) }}</span>
          </div>

          <p v-if="profileError" class="msg error">{{ profileError }}</p>
          <p v-if="profileSuccess" class="msg success">{{ profileSuccess }}</p>
        </div>

        <div class="card-footer">
          <button class="btn-outline-pill" @click="openPwModal">비밀번호 변경</button>
          <button class="btn-primary-pill" :disabled="profileLoading || !emailVerified" @click="saveProfile">
            {{ profileLoading ? '저장 중...' : '저 장' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 비밀번호 변경 모달 -->
    <div v-if="showPwModal" class="modal-overlay" @click.self="closePwModal">
      <div class="modal" :class="{ shake: pwShaking }">
        <div class="modal-header">
          <h2 class="modal-title">비밀번호 변경</h2>
          <button class="btn-modal-close" @click="closePwModal">&times;</button>
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
            {{ pwLoading ? '변경 중...' : '저장' }}
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, nextTick } from 'vue'
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
const profileLoading = ref(false)
const profileError = ref('')
const profileSuccess = ref('')
const profileShaking = ref(false)

// 이메일 분리 입력
const emailLocal = ref('')
const emailDomain = ref('')
const emailDomainSelected = ref('직접입력')
const showDomainDropdown = ref(false)
const emailLocalRef = ref(null)

const domainOptions = ['직접입력', 'gmail.com', 'naver.com', 'daum.net', 'hanmail.net']

// 이메일 인증
const emailCodeSent = ref(false)
const emailVerified = ref(false)
const emailVerifyCode = ref('')
const emailVerifyError = ref('')
const emailSending = ref(false)
const emailVerifying = ref(false)

// 비밀번호
const showPwModal = ref(false)
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

const enterEditMode = () => {
  const email = profile.email || ''
  const atIdx = email.indexOf('@')
  if (atIdx > -1) {
    emailLocal.value = email.substring(0, atIdx)
    const domain = email.substring(atIdx + 1)
    if (domainOptions.includes(domain)) {
      emailDomain.value = domain
      emailDomainSelected.value = domain
    } else {
      emailDomain.value = domain
      emailDomainSelected.value = '직접입력'
    }
  } else {
    emailLocal.value = email
    emailDomain.value = ''
    emailDomainSelected.value = '직접입력'
  }
  editMode.value = true
  emailCodeSent.value = false
  emailVerified.value = false
  emailVerifyCode.value = ''
  emailVerifyError.value = ''
  profileError.value = ''
  profileSuccess.value = ''
}

const sendEmailCode = async () => {
  emailVerifyError.value = ''
  const fullEmail = getFullEmail()
  if (!fullEmail || !fullEmail.includes('@')) {
    emailVerifyError.value = '올바른 이메일을 입력하세요.'
    return
  }
  emailSending.value = true
  try {
    await api.post('/auth/send-code', { email: fullEmail })
    emailCodeSent.value = true
    emailVerifyCode.value = ''
  } catch (err) {
    emailVerifyError.value = err.response?.data?.message || '인증코드 전송에 실패했습니다.'
  } finally {
    emailSending.value = false
  }
}

const checkEmailCode = async () => {
  emailVerifyError.value = ''
  if (!emailVerifyCode.value || emailVerifyCode.value.length !== 6) {
    emailVerifyError.value = '인증코드 6자리를 입력하세요.'
    return
  }
  emailVerifying.value = true
  try {
    const fullEmail = getFullEmail()
    await api.post('/auth/verify-code', { email: fullEmail, code: emailVerifyCode.value })
    emailVerified.value = true
  } catch (err) {
    emailVerifyError.value = err.response?.data?.message || '인증코드가 일치하지 않습니다.'
  } finally {
    emailVerifying.value = false
  }
}

const selectDomain = (d) => {
  emailDomainSelected.value = d
  if (d === '직접입력') {
    emailDomain.value = ''
  } else {
    emailDomain.value = d
  }
  showDomainDropdown.value = false
}

const onEmailInput = () => {
  profileError.value = ''
  emailCodeSent.value = false
  emailVerified.value = false
  emailVerifyCode.value = ''
  emailVerifyError.value = ''
}

const clearEmail = () => {
  emailLocal.value = ''
  emailDomain.value = ''
  emailDomainSelected.value = '직접입력'
  profileError.value = ''
  nextTick(() => {
    emailLocalRef.value?.focus()
  })
}

const getFullEmail = () => {
  if (!emailLocal.value || !emailDomain.value) return ''
  return `${emailLocal.value}@${emailDomain.value}`
}

const saveProfile = async () => {
  profileError.value = ''
  profileSuccess.value = ''

  const fullEmail = getFullEmail()
  if (!fullEmail || !fullEmail.includes('@')) {
    profileError.value = '올바른 이메일을 입력하세요.'
    triggerShake(profileShaking)
    return
  }

  profileLoading.value = true
  try {
    await api.put('/member/profile', {
      email: fullEmail
    })
    profile.email = fullEmail

    editMode.value = false
    showDomainDropdown.value = false
    profileSuccess.value = '회원정보가 수정되었습니다.'
    setTimeout(() => { profileSuccess.value = '' }, 3000)
  } catch (err) {
    profileError.value = err.response?.data?.message || '수정에 실패했습니다.'
    triggerShake(profileShaking)
  } finally {
    profileLoading.value = false
  }
}

const openPwModal = () => {
  pwForm.currentPassword = ''
  pwForm.newPassword = ''
  pwForm.confirmPassword = ''
  pwError.value = ''
  pwSuccess.value = ''
  showPwModal.value = true
}

const closePwModal = () => {
  showPwModal.value = false
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
    setTimeout(() => {
      pwSuccess.value = ''
      closePwModal()
    }, 1500)
  } catch (err) {
    pwError.value = err.response?.data?.message || '비밀번호 변경에 실패했습니다.'
    triggerShake(pwShaking)
  } finally {
    pwLoading.value = false
  }
}

onMounted(async () => {
  await fetchProfile()
})
</script>

<style scoped>
.mypage {
  width: 100%;
  min-height: calc(100vh - 120px);
  display: flex;
  flex-direction: column;
  padding: 30px 20px;
  box-sizing: border-box;
  position: relative;
}

.page-title {
  font-size: 30px;
  font-weight: 700;
  color: #1F3864;
  margin: 0 0 16px 0;
  text-align: right;
  letter-spacing: 1px;
}

/* ── 카드 래퍼: 기본값 = 단일 모드 ── */
.cards-wrap {
  display: flex;
  justify-content: center;
  gap: 18px;
  width: 100%;
  max-width: 900px;
  margin: auto auto;
  transition: all 0.35s ease;
}

/* ── 카드 공통: 기본값 = 단일 모드 ── */
.card {
  background: transparent;
  padding: 40px 32px 36px;
  flex: 1;
  min-width: 0;
  transition: all 0.35s ease;
}

/* ── 듀얼 모드 오버라이드 ── */
.cards-wrap.dual-mode {
  max-width: 900px;
  margin: 40px auto auto auto;
}

.cards-wrap.dual-mode .view-card {
  flex: 4;
  padding: 30px 16px 28px;
}

.cards-wrap.dual-mode .edit-card {
  flex: 6;
  padding: 30px 8px 28px;
}

.cards-wrap.dual-mode .card-header-center {
  margin-bottom: 20px;
}

.cards-wrap.dual-mode .card-title {
  font-size: 16px;
  font-weight: 700;
}

.cards-wrap.dual-mode .view-card .info-row {
  margin: 0 10px;
}

.cards-wrap.dual-mode .edit-card .info-row {
  margin: 0 0px;
}

.cards-wrap.dual-mode .info-label {
  font-size: 13px;
}

.cards-wrap.dual-mode .edit-card .info-label {
  width: 30%;
}

.cards-wrap.dual-mode .info-value {
  font-size: 13px;
}

.cards-wrap.dual-mode .card-footer {
  margin-top: 28px;
}

.btn-disabled {
  background: #cccccc !important;
  box-shadow: none !important;
  cursor: not-allowed !important;
  opacity: 0.7;
}

.cards-wrap.dual-mode .btn-primary-pill {
  padding: 10px 36px;
  font-size: 14px;
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

/* ── 헤더 중앙 정렬 ── */
.card-header-center {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 40px;
}

.card-title {
  font-size: 24px;
  font-weight: 800;
  color: #1F3864;
  margin: 0;
}

/* ── 프로필 정보 행 ── */
.profile-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.info-row {
  display: flex;
  align-items: center;
  margin: 0 40px;
  background: #eeeeef;
  border-radius: 9999px;
  padding: 4px;
  position: relative;
}

.info-row.last {
  /* 동일 스타일 */
}

.info-label {
  width: 45%;
  flex-shrink: 0;
  font-size: 14px;
  font-weight: 700;
  color: #1a1a1a;
  background: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 10px 0;
  border-radius: 9999px;
  position: relative;
  z-index: 2;
}

.info-value {
  flex: 1;
  text-align: center;
  font-size: 14px;
  color: #1a1a1a;
  font-weight: 700;
  background: transparent;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 10px 16px;
}

.info-value.readonly {
  color: #999;
}

/* ── 이메일 입력 ── */
.email-input-wrap {
  flex: 1;
  min-width: 0;
  margin-left: 8px;
}

.btn-verify-inline {
  flex-shrink: 0;
  margin-left: 6px;
  margin-right: 8px;
}

.btn-verified {
  background: #10B981 !important;
}

/* ── 이메일 인증 ── */
.email-verify-wrap {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 6px;
  margin-left: 10px;
}

.verify-error-msg {
  text-align: center;
  margin: 4px 0 0 0;
}

.btn-verify-send,
.btn-verify-check,
.btn-verify-resend {
  padding: 4px 12px;
  border: none;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: opacity 0.2s;
}

.btn-verify-send {
  background: #3a7fcc;
  color: #fff;
}

.btn-verify-check {
  background: #10B981;
  color: #fff;
}

.btn-verify-resend {
  background: #f0f0f0;
  color: #666;
}

.btn-verify-send:disabled,
.btn-verify-check:disabled,
.btn-verify-resend:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.verify-code-input {
  width: 90px;
  padding: 4px 8px;
  border: 1px solid #d0dae6;
  border-radius: 6px;
  font-size: 12px;
  text-align: center;
  outline: none;
}

.verify-code-input:focus {
  border-color: #5ba3e6;
}

.verify-complete {
  font-size: 12px;
  font-weight: 600;
  color: #10B981;
}

.email-field {
  display: flex;
  align-items: center;
  gap: 3px;
  position: relative;
}

.email-field input {
  padding: 4px 6px;
  border: 1px solid #d0dae6;
  border-radius: 6px;
  font-size: 12px;
  color: #1a1a1a;
  background: #f5f8fb;
  outline: none;
  transition: border-color 0.2s;
  box-sizing: border-box;
}

.email-field input:focus {
  border-color: #5ba3e6;
  background: #fff;
}

.email-field > input:first-child {
  flex: 1;
  min-width: 0;
}

.at-sign {
  font-size: 12px;
  color: #1a1a1a;
  flex-shrink: 0;
}

.domain-select-wrap {
  position: relative;
  flex: 1;
  min-width: 0;
  display: flex;
}

.domain-select-wrap input {
  flex: 1;
  min-width: 0;
  padding-right: 24px;
}

.domain-toggle {
  position: absolute;
  right: 4px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  color: #666;
  font-size: 11px;
  cursor: pointer;
  padding: 2px 4px;
  line-height: 1;
}

.domain-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: #fff;
  border: 1px solid #d0dae6;
  border-radius: 8px;
  box-shadow: 0 6px 20px rgba(30, 56, 100, 0.12);
  list-style: none;
  margin: 4px 0 0 0;
  padding: 4px 0;
  z-index: 10;
  max-height: 180px;
  overflow-y: auto;
}

.domain-dropdown li {
  padding: 8px 14px;
  font-size: 13px;
  color: #333;
  cursor: pointer;
  transition: background 0.15s;
}

.domain-dropdown li:hover {
  background: #edf4fc;
}

.domain-dropdown li.active {
  background: #ddeaf8;
  color: #2b7bd4;
  font-weight: 600;
}

.btn-clear-email {
  background: none;
  border: none;
  color: #aab5c4;
  font-size: 18px;
  cursor: pointer;
  padding: 0 4px;
  line-height: 1;
  flex-shrink: 0;
}

.btn-clear-email:hover {
  color: #e74c3c;
}

/* ── 하단 버튼 영역 ── */
.card-footer {
  display: flex;
  justify-content: center;
  gap: 10px;
  margin-top: 32px;
  padding-top: 4px;
}

.btn-primary-pill {
  padding: 10px 120px;
  background: #0088ff;
  color: #fff;
  border: none;
  border-radius: 24px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s, box-shadow 0.2s;
  letter-spacing: 2px;
  box-shadow: 0 2px 8px rgba(58, 127, 204, 0.25);
}

.btn-primary-pill:hover:not(:disabled) {
  opacity: 0.9;
  box-shadow: 0 4px 14px rgba(58, 127, 204, 0.35);
}

.btn-primary-pill:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-outline-pill {
  padding: 8px 20px;
  background: #fff;
  color: #3a7fcc;
  border: 1.5px solid #5ba3e6;
  border-radius: 24px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-outline-pill:hover {
  background: #edf4fc;
}

/* ── 메시지 ── */
.msg {
  font-size: 13px;
  text-align: center;
  margin: 10px 0 0 0;
  font-weight: 500;
}

.msg.error {
  color: #e74c3c;
}

.msg.success {
  color: #10B981;
}

/* ══════════════════════════════════
   비밀번호 변경 모달
   ══════════════════════════════════ */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.40);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: #fff;
  border-radius: 20px;
  padding: 32px 36px;
  width: 400px;
  max-width: 90vw;
  box-shadow: 0 8px 36px rgba(0, 0, 0, 0.18);
}

.modal.shake {
  animation: shake 0.45s ease-in-out;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
  padding-bottom: 14px;
  border-bottom: 1px solid #e8ecf1;
}

.modal-title {
  font-size: 17px;
  font-weight: 700;
  color: #1F3864;
  margin: 0;
}

.btn-modal-close {
  background: none;
  border: none;
  font-size: 22px;
  color: #aab5c4;
  cursor: pointer;
  padding: 0;
  line-height: 1;
}

.btn-modal-close:hover {
  color: #333;
}

/* ── 비밀번호 폼 ── */
.pw-form {
  display: flex;
  flex-direction: column;
  gap: 18px;
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
  border: 1px solid #d0dae6;
  border-radius: 8px;
  font-size: 14px;
  color: #1a1a1a;
  background: #f5f8fb;
  outline: none;
  transition: border-color 0.2s;
}

.form-group input::placeholder {
  color: #b0bcc9;
}

.form-group input:focus {
  border-color: #5ba3e6;
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

.btn-submit {
  padding: 12px;
  background: linear-gradient(135deg, #5ba3e6 0%, #3a7fcc 100%);
  color: #fff;
  border: none;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s;
}

.btn-submit:hover:not(:disabled) {
  opacity: 0.9;
}

.btn-submit:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ── 반응형 ── */
@media (max-width: 768px) {
  .cards-wrap.dual-mode {
    flex-direction: column;
    max-width: 440px;
  }

  .email-field {
    flex-wrap: wrap;
  }

  .email-field > input:first-child {
    width: 100%;
    flex: none;
  }

  .at-sign {
    display: none;
  }

  .domain-select-wrap {
    width: 100%;
    flex: none;
    margin-top: 6px;
  }
}
</style>
