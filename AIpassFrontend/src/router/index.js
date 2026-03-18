import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/LoginView.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/signup',
    name: 'Signup',
    component: () => import('../views/SignupView.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/find-account',
    name: 'FindAccount',
    component: () => import('../views/FindAccountView.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    component: () => import('../components/MainLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: () => import('../views/DashboardView.vue')
      },
      {
        path: 'mypage',
        name: 'MyPage',
        component: () => import('../views/MypageView.vue')
      },
      {
        path: 'traffic',
        name: 'Traffic',
        component: () => import('../views/TrafficView.vue')
      },
      {
        path: 'cctv',
        name: 'Cctv',
        component: () => import('../views/CctvView.vue')
      },
      {
        path: 'enforcement',
        name: 'Enforcement',
        component: () => import('../views/EnforcementView.vue')
      },
      {
        path: 'predictive',
        name: 'Predictive',
        component: () => import('../views/PredictiveView.vue')
      },
      {
        path: 'statistics',
        name: 'Statistics',
        component: () => import('../views/StatisticsView.vue')
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()

  // 최초 진입 시 세션 확인
  if (!auth.isLoggedIn) {
    await auth.checkSession()
  }

  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    return '/login'
  }

  if (!to.meta.requiresAuth && auth.isLoggedIn && (to.name === 'Login' || to.name === 'Signup')) {
    return '/'
  }
})

export default router
