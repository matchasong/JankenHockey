<template>
  <div class="app-container">
    <!-- ログインユーザー表示（右上） -->
    <div v-if="showUserDisplay" class="user-display">
      {{ playerName }}
      <button class="logout-btn" @click="logout">ログアウト</button>
    </div>
    <router-view />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { logout as authLogout } from '@/utils/auth'

const route = useRoute()
const router = useRouter()
const playerName = ref('')

// ユーザー表示を表示するかどうか
const showUserDisplay = computed(() => {
  const routeName = route.name
  // Login画面とGame画面では表示しない
  if (routeName === 'Login' || routeName === 'Game') {
    return false
  }
  // プレイヤー名があり、認証されている場合のみ表示
  return playerName.value && sessionStorage.getItem('authToken')
})

// セッションストレージからプレイヤー名を取得
const updatePlayerName = () => {
  playerName.value = sessionStorage.getItem('playerName') || ''
}

onMounted(() => {
  updatePlayerName()
})

// ルート変更時にプレイヤー名を更新
watch(() => route.name, () => {
  updatePlayerName()
})

// セッションストレージの変更を監視
window.addEventListener('storage', updatePlayerName)

// ログアウト処理
const logout = () => {
  authLogout(router)
}
</script>

<style src="./assets/css/app.css" scoped></style>
