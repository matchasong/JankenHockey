<template>
  <div class="room-list-container">
    <div class="room-list-header">
      <h2 class="room-list-title">ルーム一覧</h2>
    </div>
    <div class="reload-container">
    <button class="reload-btn" @click="fetchRooms" title="再読み込み">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M12 4V1L7 6l5 5V7c3.31 0 6 2.69 6 6 0 3.31-2.69 6-6 6s-6-2.69-6-6H4c0 4.42 3.58 8 8 8s8-3.58 8-8-3.58-8-8-8z" fill="#2b3a55"/>
        </svg>
    </button>
    </div>
    <ul class="room-list-ul">
      <li v-for="room in waitingRooms" :key="room.roomId" class="room-list-li">
        <input type="hidden" :value="room.roomId" />
        <span>待機中: {{ room.creatorName }}</span>
        <span>｜メッセージ: {{ room.message }}</span>
        <button class="join-btn" @click="joinRoom(room.roomId)" :disabled="!playerName.trim()">参加(ゲーム開始)</button>
      </li>
    </ul>
    <div class="room-list-actions">
      <button class="create-room" @click="goToCreateRoom">ルーム作成</button>
      <button class="cpu-battle" @click="goToCpuBattle">CPU対戦</button>
      <button class="back" @click="goBack">戻る</button>
    </div>
  </div>
</template>

<script>
import { fetchRooms, joinRoom as joinRoomApi } from '@/api/room';
import { isAuthenticated } from '@/utils/auth';

export default {
  name: 'RoomList',
  data() {
    return {
      rooms: [],
      playerName: sessionStorage.getItem('playerName') || this.$route.query.playerName || '', // sessionStorageから取得
      isUserAuthenticated: false,
      intervalId: null
    }
  },
  computed: {
    waitingRooms() {
      // 2人揃っていないルームのみ表示
      return this.rooms.filter(room => (room.playerCount || 1) < (room.maxPlayers || 2));
    }
  },
  mounted() {
    this.checkAuthentication()
    this.fetchRooms();
    this.intervalId = setInterval(this.fetchRooms, 10000); // 10秒ごとにルーム一覧を取得する
  },
  beforeUnmount() {
    if (this.intervalId) {
      clearInterval(this.intervalId)
    }
  },
  methods: {
    checkAuthentication() {
      this.isUserAuthenticated = isAuthenticated()
    },
    async fetchRooms() {
      this.rooms = await fetchRooms();
    },
    async joinRoom(roomId) {
      try {
        if (!this.playerName.trim()) {
          alert('プレイヤー名を入力してください');
          return;
        }

        // 確認ダイアログを最初に表示
        const confirmed = confirm(`ルームに参加します。よろしいですか。`);
        if (!confirmed) {
          return; // キャンセルされた場合は何もしない
        }

        // playerNameをsessionStorageに保存
        sessionStorage.setItem('playerName', this.playerName.trim());
        const response = await joinRoomApi(roomId, this.playerName.trim());

        // ルーム参加後にゲーム画面に遷移（パラメータ付き）
        this.$router.push({
          name: 'Game',
          query: {
            roomId: response.roomId || roomId,
            playerName: this.playerName.trim(),
            isRoomCreator: false // ルーム作成者フラグを追加
          }
        });
      } catch (error) {
        if (error.message === 'NOT_ACCESSIBLE') {
          alert('参加に失敗しました。ルームの作成者が接続を切断しています。別のルームを選択してください');
        } if (error.message === 'ROOM_FULL') {
          alert('参加に失敗しました。すでにルームが埋まっています。別のルームを選択してください');
        } else {
          alert('参加に失敗しました。別のルームを選択してください。');
        }
      }
    },
    goToCreateRoom() {
      this.$router.push('/room/create');
    },
    goBack() {
      this.$router.push({ name: 'TopView' });
    },
    goToCpuBattle() {
      // Use existing player name if authenticated, otherwise use guest name
      const playerName = this.isUserAuthenticated && this.playerName.trim()
        ? this.playerName.trim()
        : 'ゲスト';

      sessionStorage.setItem('playerName', playerName);

      // Navigate directly to CPU battle
      this.$router.push({
        name: 'Game',
        query: {
          playerName: playerName,
          isCpuBattle: true
        }
      });
    }
  },
  watch: {
    playerName(newVal) {
      sessionStorage.setItem('playerName', newVal.trim());
    }
  }
}
</script>

<style scoped>
@import "@/assets/css/room-list.css";
</style>
