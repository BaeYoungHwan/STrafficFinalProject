import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const isLoggedIn = ref(false)

  async function login(username, password) {
    const res = await api.post('/auth/login', { username, password })
    user.value = res.data
    isLoggedIn.value = true
    return res.data
  }

  async function logout() {
    try {
      await api.post('/auth/logout')
    } finally {
      user.value = null
      isLoggedIn.value = false
    }
  }

  async function checkSession() {
    try {
      const res = await api.get('/auth/check')
      user.value = res.data
      isLoggedIn.value = true
      return true
    } catch {
      user.value = null
      isLoggedIn.value = false
      return false
    }
  }

  return { user, isLoggedIn, login, logout, checkSession }
})
