<template>
  <div class="not-found-container">
    <div class="not-found-content">
      <h1 class="error-code">404</h1>
      <h2 class="error-message">ページが見つかりません</h2>
      <p class="error-description">
        お探しのページは存在しないか、アクセス権限がありません。
      </p>
      <div class="action-buttons">
        <button @click="goHome" class="home-button">
          トップページに戻る
        </button>
        <button @click="goLogin" class="login-button">
          ログイン
        </button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'NotFoundPage',
  methods: {
    goHome() {
      this.$router.push({ name: 'TopView' });
    },
    goLogin() {
      this.$router.push({ name: 'Login' });
    }
  }
};
</script>

<style src="./assets/css/not-found.css" scoped></style>