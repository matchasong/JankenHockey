<template>
  <div class="top-container">
    <h1>Janken Hockey</h1>
    <div class="desc">
      オンライン対戦かCPU対戦か選んで、ゲームを始めよう！
    </div>
    <fieldset class="button-group">
      <legend>オンライン対戦（要ログイン）</legend>
      <button class="top-btn" @click="goTo('RoomList')">ルーム一覧を見る</button>
      <button class="top-btn" @click="goTo('CreateRoom')">新しいルームを作成</button>
    </fieldset>
    <fieldset class="button-group">
      <legend>CPU対戦（ログイン不要）</legend>
      <button class="top-btn cpu-battle-btn" @click="goToCpuBattle()">CPUと対戦する</button>
    </fieldset>
    <footer>&copy; 2025 Janken Hockey Project</footer>
  </div>
</template>

<script>
import { isAuthenticated } from './utils/auth'

export default {
  name: 'TopView',
  data() {
    return {
      isUserAuthenticated: false
    }
  },
  mounted() {
    this.checkAuthentication()
  },
  methods: {
    checkAuthentication() {
      this.isUserAuthenticated = isAuthenticated()
    },
    goTo(page) {
      // Check for authentication token
      const authToken = sessionStorage.getItem('authToken');
      const idToken = sessionStorage.getItem('idToken');
      const playerName = sessionStorage.getItem('playerName');
      
      if (authToken && playerName && playerName.trim() && idToken && idToken.trim()) {
        this.$router.push({ name: page });
      } else {
        // Clear any old data and redirect to login
        sessionStorage.removeItem('authToken');
        sessionStorage.removeItem('playerName');
        sessionStorage.removeItem('username');
        sessionStorage.removeItem('idToken');
        this.$router.push({ name: 'Login' });
      }
    },
    goToCpuBattle() {
      // Generate a temporary guest name for CPU battle
      const guestName = 'ゲスト';
      sessionStorage.setItem('playerName', guestName);
      
      // Navigate directly to CPU battle without authentication
      this.$router.push({
        name: 'Game',
        query: {
          playerName: guestName,
          isCpuBattle: true
        }
      });
    }
  }
}
</script>

<style src="./assets/css/top-view.css"></style>
