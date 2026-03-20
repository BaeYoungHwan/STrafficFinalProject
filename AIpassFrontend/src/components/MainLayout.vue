<template>
  <div class="main-layout">
    <Header />
    <Sidebar />
    <div class="content-area">
      <aside class="side-panel left-panel"></aside>
      <main class="main-content">
        <router-view />
      </main>
      <aside class="side-panel right-panel"></aside>
    </div>
    <Footer />
  </div>
</template>

<script setup>
import Header from './Header.vue'
import Sidebar from './Sidebar.vue'
import Footer from './Footer.vue'
</script>

<style scoped>
.main-layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  max-width: 1280px;
  margin: 0 auto;
  background: #FFFFFF;
}

.content-area {
  flex: 1;
  display: flex;
  background: #F4F6FA;
}

.side-panel {
  width: 0px;
  min-width: 0px;
  background: #FFFFFF;
}

.main-content {
  flex: 1;
  padding: 24px 32px;
  background: #F4F6FA;
}
</style>
