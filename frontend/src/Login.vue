<template>
  <div class="login-container">
    <div class="login-dialog">
      <div class="login-title">{{ isSignup ? 'アカウントを作成' : 'ログイン' }}</div>
      <div class="login-form">
        <div class="form-group">
          <label>ユーザー名</label>
          <input
            v-model="username"
            placeholder="ユーザー名を入力"
            class="login-input"
            @keyup.enter="handleSubmit"
          />
        </div>
        <div class="form-group">
          <label>パスワード</label>
          <input
            v-model="password"
            type="password"
            placeholder="パスワードを入力"
            class="login-input"
            @keyup.enter="handleSubmit"
          />
        </div>
        <div v-if="errorMessage" class="error-message">{{ errorMessage }}</div>
        <div class="login-actions">
          <button :disabled="!username.trim() || !password.trim() || isLoading" @click="handleSubmit" class="login-ok">
            {{ isLoading ? '処理中...' : (isSignup ? '作成' : 'ログイン') }}
          </button>
          <button @click="toggleMode" class="login-toggle">
            {{ isSignup ? 'ログインに戻る' : '新規アカウント作成' }}
          </button>
          <button @click="goBack" class="login-back">
            戻る
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { API_AUTH } from './api/endpoints'
import './assets/css/login.css'

const router = useRouter()
const route = useRoute()

const username = ref('')
const password = ref('')
const isSignup = ref(false)
const errorMessage = ref('')
const isLoading = ref(false)

function toggleMode() {
  isSignup.value = !isSignup.value
  errorMessage.value = ''
}

function goBack() {
  router.push({ name: 'TopView' })
}

async function handleSubmit() {
  if (!username.value.trim() || !password.value.trim()) {
    return
  }

  isLoading.value = true
  errorMessage.value = ''

  try {
    const response = await fetch(API_AUTH, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        action: isSignup.value ? 'signup' : 'login',
        username: username.value.trim(),
        password: password.value
      })
    })

    const data = await response.json()

    if (response.ok) {
      // Store authentication data
      sessionStorage.setItem('authToken', data.token)     // Web Socket用AccessToken
      sessionStorage.setItem('idToken', data.idToken)    // API Gateway用IdToken
      sessionStorage.setItem('playerName', data.username)
      sessionStorage.setItem('username', data.username)

      // Navigate to the intended page
      const next = route.query.next || 'RoomList'
      router.push({ name: next })
    } else {
      errorMessage.value = data.error || 'システムエラーが発生しました'
    }
  } catch (error) {
    console.error('Authentication error')
    errorMessage.value = 'システムエラーが発生しました'
  } finally {
    isLoading.value = false
  }
}
</script>
