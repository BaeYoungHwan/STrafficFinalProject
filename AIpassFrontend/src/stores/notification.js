import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api/index'

export const useNotificationStore = defineStore('notification', () => {
  const notifications = ref([])
  const unreadCount = ref(0)
  const violationTick = ref(0)
  let eventSource = null

  // SSE 연결
  function connect() {
    if (eventSource) return // 중복 연결 방지
    eventSource = new EventSource('/api/notifications/stream', { withCredentials: true })

    eventSource.addEventListener('notification', (e) => {
      const data = JSON.parse(e.data)
      notifications.value.unshift(data)
      unreadCount.value++
      if (data.eventType === 'VIOLATION') violationTick.value++
    })

    eventSource.onerror = () => {
      disconnect()
      setTimeout(connect, 3000) // 3초 후 재연결
    }
  }

  function disconnect() {
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }
  }

  // 초기 알림 목록 로드
  async function fetchInitial() {
    try {
      const res = await api.get('/notifications')
      if (res.data.success) {
        notifications.value = res.data.data.items
        unreadCount.value = res.data.data.unreadCount
      }
    } catch (e) {
      /* 조용히 실패 */
    }
  }

  async function markAsRead(id) {
    try {
      await api.put(`/notifications/${id}/read`)
      const item = notifications.value.find((n) => n.notificationId === id)
      if (item && !item.isRead) {
        item.isRead = true
        unreadCount.value = Math.max(0, unreadCount.value - 1)
      }
    } catch (e) {
      /* 조용히 실패 */
    }
  }

  async function markAllRead() {
    try {
      await api.put('/notifications/read-all')
      notifications.value.forEach((n) => {
        n.isRead = true
      })
      unreadCount.value = 0
    } catch (e) {
      /* 조용히 실패 */
    }
  }

  return {
    notifications,
    unreadCount,
    violationTick,
    connect,
    disconnect,
    fetchInitial,
    markAsRead,
    markAllRead
  }
})
