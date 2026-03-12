import { createRouter, createWebHistory } from 'vue-router'
import LoginView from '../views/LoginView.vue'
import SignupView from '../views/SignupView.vue'
import PublicMainView from '../views/PublicMainView.vue'
import DashboardView from '../views/DashboardView.vue'
import CctvView from '../views/CctvView.vue'
import TrafficView from '../views/TrafficView.vue'
import ViolationView from '../views/ViolationView.vue'
import PredictView from '../views/PredictView.vue'
import StatsView from '../views/StatsView.vue'

const routes = [
  {
    path: '/',
    name: 'login',
    component: LoginView,
  },
  {
    path: '/signup',
    name: 'signup',
    component: SignupView,
  },
  {
    path: '/main',
    component: PublicMainView,
    children: [
      {
        path: '',
        redirect: '/main/dashboard',
      },
      {
        path: 'dashboard',
        name: 'dashboard',
        component: DashboardView,
      },
      {
        path: 'traffic',
        name: 'traffic',
        component: TrafficView,
      },
      {
        path: 'cctv',
        name: 'cctv',
        component: CctvView,
      },
      {
        path: 'violation',
        name: 'violation',
        component: ViolationView,
      },
      {
        path: 'predict',
        name: 'predict',
        component: PredictView,
      },
      {
        path: 'stats',
        name: 'stats',
        component: StatsView,
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router