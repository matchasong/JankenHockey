<template>
  <div class="create-room-container">
    <div class="create-room-header">
      <h2 class="create-room-title">ルーム作成</h2>
    </div>
    <form class="create-room-form" @submit.prevent="handleCreateRoom">
      <div>
        <label>メッセージ(任意):</label>
        <input v-model="message" />
      </div>
      <div v-if="error" style="color:red">{{ error }}</div>
      <div class="create-room-actions">
        <button type="submit" class="create" :disabled="!playerName.trim()">作成</button>
        <button type="button" class="cancel" @click="goBack">戻る</button>
      </div>
    </form>
  </div>
</template>

<script>
import { createRoom } from '@/api/room';
import { isAuthenticated } from '@/utils/auth';

export default {
  name: 'CreateRoom',
  data() {
    return {
      playerName: sessionStorage.getItem('playerName') || this.$route.query.playerName || '',
      message: '',
      error: '',
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
    async handleCreateRoom() {
      try {
        if (!this.playerName.trim()) {
          this.error = 'プレイヤー名を入力してください';
          return;
        }
        // playerNameをsessionStorageに保存
        sessionStorage.setItem('playerName', this.playerName.trim());
        const response = await createRoom({ creatorName: this.playerName, message: this.message });
        // ルーム作成後にゲーム画面（Game）に遷移（パラメータ付き）
        this.$router.push({
          name: 'Game',
          query: {
            roomId: response.roomId,
            playerName: this.playerName.trim(),
            isRoomCreator: true // ルーム作成者フラグを追加
          }
        });
      } catch {
        this.error = 'ルーム作成に失敗しました';
      }
    },
    goBack() {
      this.$router.push({ name: 'TopView'});
    }
  }
}
</script>

<style scoped>
@import "@/assets/css/create-room.css";
</style>
