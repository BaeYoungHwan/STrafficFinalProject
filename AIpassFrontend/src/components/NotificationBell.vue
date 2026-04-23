<template>
  <div class="notification-wrapper" ref="wrapperRef">
    <!-- 벨 아이콘 버튼 -->
    <button class="bell-btn" @click="togglePanel" :aria-label="`알림 ${unreadCount}개`">
      <svg
        class="bell-icon"
        :class="{ 'has-unread': unreadCount > 0 }"
        width="20"
        height="20"
        viewBox="0 0 24 24"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path
          d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
        <path
          d="M13.73 21a2 2 0 0 1-3.46 0"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
      </svg>
      <!-- 미읽음 뱃지 -->
      <span v-if="unreadCount > 0" class="badge">
        {{ unreadCount > 99 ? '99+' : unreadCount }}
      </span>
    </button>

    <!-- 드롭다운 패널 -->
    <Transition name="panel">
      <div v-if="isOpen" class="notification-panel">
        <!-- 패널 헤더 -->
        <div class="panel-header">
          <span class="panel-title">알림</span>
          <button
            v-if="notifications.length > 0"
            class="btn-mark-all"
            @click="handleMarkAllRead"
          >
            모두 읽음
          </button>
        </div>

        <!-- 알림 목록 -->
        <div class="panel-body">
          <template v-if="notifications.length > 0">
            <div
              v-for="item in notifications"
              :key="item.notificationId"
              class="notification-item"
              :class="{ unread: !item.isRead }"
              @click="handleItemClick(item)"
            >
              <!-- 타입 아이콘 -->
              <div class="item-icon" :class="getTypeClass(item.type)">
                <svg
                  v-if="item.type === 'VIOLATION'"
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                  />
                  <line
                    x1="12"
                    y1="9"
                    x2="12"
                    y2="13"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linecap="round"
                  />
                  <line
                    x1="12"
                    y1="17"
                    x2="12.01"
                    y2="17"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linecap="round"
                  />
                </svg>
                <svg
                  v-else-if="item.type === 'EQUIPMENT_FAILURE'"
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <circle cx="12" cy="12" r="3" stroke="currentColor" stroke-width="2" />
                  <path
                    d="M19.07 4.93a10 10 0 0 1 0 14.14M4.93 4.93a10 10 0 0 0 0 14.14"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linecap="round"
                  />
                </svg>
                <svg
                  v-else
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2" />
                  <line
                    x1="12"
                    y1="8"
                    x2="12"
                    y2="12"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linecap="round"
                  />
                  <line
                    x1="12"
                    y1="16"
                    x2="12.01"
                    y2="16"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linecap="round"
                  />
                </svg>
              </div>

              <!-- 내용 -->
              <div class="item-content">
                <p class="item-message">{{ item.message }}</p>
                <span class="item-time">{{ formatDate(item.createdAt) }}</span>
              </div>

              <!-- 미읽음 점 -->
              <span v-if="!item.isRead" class="unread-dot" />
            </div>
          </template>

          <!-- 알림 없음 -->
          <div v-else class="empty-state">
            <svg
              width="40"
              height="40"
              viewBox="0 0 24 24"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              class="empty-icon"
            >
              <path
                d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"
                stroke="#CBD5E0"
                stroke-width="1.5"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
              <path
                d="M13.73 21a2 2 0 0 1-3.46 0"
                stroke="#CBD5E0"
                stroke-width="1.5"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
            <p class="empty-text">새로운 알림이 없습니다</p>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { useNotificationStore } from '../stores/notification'
import { storeToRefs } from 'pinia'

const router = useRouter()
const notificationStore = useNotificationStore()
const { notifications, unreadCount } = storeToRefs(notificationStore)

const isOpen = ref(false)
const wrapperRef = ref(null)

// 패널 토글: 열릴 때 전체 읽음 처리
function togglePanel() {
  isOpen.value = !isOpen.value
  if (isOpen.value && unreadCount.value > 0) {
    notificationStore.markAllRead()
  }
}

// 개별 항목 클릭
function handleItemClick(item) {
  if (!item.isRead) {
    notificationStore.markAsRead(item.notificationId)
  }
  isOpen.value = false
  if (item.type === 'VIOLATION') {
    router.push('/enforcement')
  } else if (item.type === 'EQUIPMENT_FAILURE') {
    router.push('/predictive')
  }
}

// 모두 읽음 버튼
async function handleMarkAllRead() {
  await notificationStore.markAllRead()
}

// 타입별 CSS 클래스
function getTypeClass(type) {
  if (type === 'VIOLATION') return 'type-violation'
  if (type === 'EQUIPMENT_FAILURE') return 'type-equipment'
  return 'type-default'
}

// 날짜 포맷: MM/DD HH:mm
function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return dateStr
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  const hh = String(d.getHours()).padStart(2, '0')
  const min = String(d.getMinutes()).padStart(2, '0')
  return `${mm}/${dd} ${hh}:${min}`
}

// 외부 클릭 감지
function handleClickOutside(e) {
  if (wrapperRef.value && !wrapperRef.value.contains(e.target)) {
    isOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener('mousedown', handleClickOutside)
})

onBeforeUnmount(() => {
  document.removeEventListener('mousedown', handleClickOutside)
})
</script>

<style scoped>
.notification-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

/* 벨 버튼 */
.bell-btn {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  background: none;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  padding: 0;
  transition: background 0.15s;
}

.bell-btn:hover {
  background: #F1F5F9;
}

.bell-icon {
  color: #6B7280;
  transition: color 0.15s;
}

.bell-icon.has-unread {
  color: #1A6DCC;
}

/* 미읽음 뱃지 */
.badge {
  position: absolute;
  top: 2px;
  right: 2px;
  min-width: 16px;
  height: 16px;
  padding: 0 3px;
  background: #EF4444;
  color: #ffffff;
  font-size: 10px;
  font-weight: 700;
  line-height: 16px;
  text-align: center;
  border-radius: 9999px;
  box-sizing: border-box;
  font-family: 'Pretendard', system-ui, sans-serif;
}

/* 드롭다운 패널 */
.notification-panel {
  position: absolute;
  top: calc(100% + 10px);
  right: 0;
  width: 320px;
  max-height: 400px;
  display: flex;
  flex-direction: column;
  background: #ffffff;
  border: 1px solid #E2E8F0;
  border-radius: 16px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  z-index: 1000;
  overflow: hidden;
  font-family: 'Pretendard', system-ui, sans-serif;
}

/* 패널 헤더 */
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px 12px;
  border-bottom: 1px solid #E2E8F0;
  flex-shrink: 0;
}

.panel-title {
  font-size: 15px;
  font-weight: 700;
  color: #1A1A2E;
}

.btn-mark-all {
  background: none;
  border: none;
  font-size: 12px;
  font-weight: 500;
  color: #1A6DCC;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 6px;
  transition: background 0.15s;
  font-family: 'Pretendard', system-ui, sans-serif;
}

.btn-mark-all:hover {
  background: #E8F1FB;
}

/* 패널 본문 */
.panel-body {
  overflow-y: auto;
  flex: 1;
}

/* 알림 항목 */
.notification-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 16px;
  cursor: pointer;
  background: #ffffff;
  transition: background 0.12s;
  border-bottom: 1px solid #F1F5F9;
}

.notification-item:last-child {
  border-bottom: none;
}

.notification-item:hover {
  background: #F8FAFC;
}

.notification-item.unread {
  background: #E8F1FB;
}

.notification-item.unread:hover {
  background: #D6E8F8;
}

/* 타입 아이콘 */
.item-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  flex-shrink: 0;
  margin-top: 1px;
}

.type-violation {
  background: #FEE2E2;
  color: #EF4444;
}

.type-equipment {
  background: #FEF3C7;
  color: #F59E0B;
}

.type-default {
  background: #E8F1FB;
  color: #1A6DCC;
}

/* 내용 */
.item-content {
  flex: 1;
  min-width: 0;
}

.item-message {
  margin: 0 0 4px;
  font-size: 13px;
  font-weight: 500;
  color: #1A1A2E;
  line-height: 1.4;
  word-break: keep-all;
}

.item-time {
  font-size: 11px;
  color: #94A3B8;
  font-weight: 400;
}

/* 미읽음 점 */
.unread-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #1A6DCC;
  flex-shrink: 0;
  margin-top: 6px;
}

/* 빈 상태 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  gap: 12px;
}

.empty-icon {
  opacity: 0.5;
}

.empty-text {
  margin: 0;
  font-size: 13px;
  color: #94A3B8;
  font-weight: 400;
}

/* 패널 등장 애니메이션 */
.panel-enter-active,
.panel-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.panel-enter-from,
.panel-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
</style>
