<template>
  <footer class="app-footer">
    <div class="footer-divider"></div>
    <div class="footer-inner-wrap">
    <div class="footer-inner">
      <div class="footer-members">
        <span>BAE YOUNGWHAN</span>
        <span class="divider">|</span>
        <span>KIM SOYEON</span>
        <span class="divider">|</span>
        <span>HA JAEYOUNG</span>
       </div>
      <div class="footer-logos">
        <img :src="kdtLogo" alt="K-Digital Training" class="logo-img" />
        <img :src="itsKoreaLogo" alt="ITS KOREA" class="logo-img" />
        <img :src="mbcLogo" alt="MBC아카데미 컴퓨터교육센터" class="logo-img" />
        <img :src="sTrafficLogo" alt="S-Traffic" class="logo-img" />
      </div>
      <div class="footer-brand">
        <svg class="footer-logo-icon" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="2" y1="12" x2="22" y2="12" /><line x1="12" y1="2" x2="12" y2="22" />
          <path d="M20 16c-4 0-6-2-6-6s2-6 6-6" /><path d="M4 8c4 0 6 2 6 6s-2 6-6 6" />
        </svg>
        <span>AI-Pass</span>
      </div>
    </div>
    </div>
  </footer>

</template>

<script setup>
import kdtLogo from '../assets/logos/KDT.png'
import itsKoreaLogo from '../assets/logos/its-korea.png'
import mbcLogo from '../assets/logos/mbc-academy.png'
import sTrafficLogo from '../assets/logos/s-traffic.png'
</script>

<style scoped>
.app-footer {
  margin-top: auto;
}

.footer-divider {
  height: 3px;
  background: #E2E8F0;
}

.footer-inner-wrap {
  padding: 14px 16px 12px;
}

.footer-inner {
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  border-radius: 14px;
  padding: 16px 24px;
  text-align: center;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.2);
}

.footer-members {
  font-size: 13px;
  font-weight: 600;
  color: #1A1A2E;
  margin-bottom: 10px;
  letter-spacing: 0.5px;
}

.footer-members .divider {
  margin: 0 8px;
  color: #E2E8F0;
}

.footer-logos {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 24px;
  margin-bottom: 10px;
}

.logo-img {
  height: 32px;
  width: auto;
  object-fit: contain;
  opacity: 0.7;
  transition: opacity 0.2s;
}

.logo-img:hover {
  opacity: 1;
}

.footer-brand {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  font-size: 18px;
  font-weight: 700;
  color: #1A1A2E;
}

.footer-logo-icon {
  color: #1A6DCC;
  width: 20px;
  height: 20px;
}
</style>
