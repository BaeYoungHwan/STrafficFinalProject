<template>
  <nav class="app-gnb">
    <div class="gnb-bar">
      <template v-for="(item, idx) in menuItems" :key="item.path">
        <router-link
          :to="item.path"
          class="gnb-item"
          :class="{ active: isActive(item.path) }"
        >
          {{ item.label }}
        </router-link>
        <span v-if="idx < menuItems.length - 1" class="gnb-divider">|</span>
      </template>
      <button class="gnb-expand" title="더보기">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="9 18 15 12 9 6" />
        </svg>
      </button>
    </div>
  </nav>
</template>

<script setup>
import { useRoute } from 'vue-router'

const route = useRoute()

const menuItems = [
  { label: '메인', path: '/' },
{ label: 'CCTV', path: '/cctv' },
  { label: '단속 내역', path: '/enforcement' },
  { label: '설비 예지보전', path: '/predictive' }
]

const isActive = (path) => {
  if (path === '/') return route.path === '/'
  return route.path.startsWith(path)
}
</script>

<style scoped>
.app-gnb {
  display: flex;
  justify-content: center;
  padding: 6px 40px;
  background: #FFFFFF;
}

.gnb-bar {
  display: inline-flex;
  align-items: center;
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  border-radius: 28px;
  padding: 0 12px;
}

.gnb-item {
  padding: 7px 16px;
  font-size: 13px;
  font-weight: 500;
  color: #6B7280;
  text-decoration: none;
  transition: color 0.2s;
  white-space: nowrap;
}

.gnb-item:hover {
  color: #1A1A2E;
}

.gnb-item.active {
  color: #1A6DCC;
  font-weight: 700;
}

.gnb-divider {
  color: #E2E8F0;
  font-size: 16px;
  user-select: none;
}

.gnb-expand {
  padding: 10px;
  background: none;
  border: none;
  color: #6B7280;
  cursor: pointer;
  display: flex;
  align-items: center;
  transition: color 0.2s;
}

.gnb-expand svg {
  width: 20px;
  height: 20px;
}

.gnb-expand:hover {
  color: #1A1A2E;
}
</style>
