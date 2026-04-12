<template>
  <div id="app">
    <el-container>
      <el-header>
        <h1>ASIN 排名追踪器</h1>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
      <el-footer>
        <p>&copy; 2026 ASIN Ranker. All rights reserved.</p>
      </el-footer>
    </el-container>
  </div>
</template>

<script setup lang="ts">
// 根组件
</script>

<style scoped>
#app {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Helvetica Neue', sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  height: 100vh;
}

.el-container {
  height: 100%;
}

.el-header {
  background-color: #409EFF;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.el-header h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
}

.el-main {
  background-color: #f5f7fa;
  padding: 20px;
}

.el-footer {
  background-color: #fff;
  text-align: center;
  line-height: 60px;
  border-top: 1px solid #e6e6e6;
}

.el-footer p {
  margin: 0;
  color: #909399;
  font-size: 14px;
}
</style>
