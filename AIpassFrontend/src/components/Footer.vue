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
        <a href="https://www.moel.go.kr/index.do" target="_blank" rel="noopener noreferrer">
          <img :src="kdtLogo" alt="K-Digital Training" class="logo-img" />
        </a>
        <a href="https://itskorea.kr/main.do" target="_blank" rel="noopener noreferrer">
          <img :src="itsKoreaLogo" alt="ITS KOREA" class="logo-img" />
        </a>
        <a href="https://www.mbccomputer.co.kr/front/home" target="_blank" rel="noopener noreferrer">
          <img :src="mbcLogo" alt="MBC아카데미 컴퓨터교육센터" class="logo-img" />
        </a>
        <a href="https://www.straffic.co.kr/" target="_blank" rel="noopener noreferrer">
          <img :src="sTrafficLogo" alt="S-Traffic" class="logo-img" />
        </a>
      </div>
      <div class="footer-brand">
        <img :src="aipassLogo" alt="AI-PASS" class="footer-logo-img" />
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
import aipassLogo from '../assets/logos/AI-PASS_LOGO.png'
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

.footer-logo-img {
  height: 28px;
  object-fit: contain;
}
</style>
