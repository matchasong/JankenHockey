<template>
  <div class="board">
    <svg :viewBox="`0 0 ${svgWidth} ${svgHeight}`" preserveAspectRatio="xMidYMid meet" width="100%" height="100%" style="background:#fff; border:1px solid #aaa;">
      <!-- ボール描画 -->
      <image v-for="ball in board.balls" :key="ball.id"
        :x="toScreenX(ball.x) - 19.2" :y="toScreenY(ball.y) - 19.2" 
        width="50" height="50"
        :href="colorToSvg(ball.color)"
      />
      <!-- 発射台（横移動可能な長方形） -->
      <rect
        :x="launcherCenterX - 30"
        :y="launcherCenterY - 10"
        width="60"
        height="20"
        fill="#ffb74d"
        stroke="#ff9800"
        stroke-width="3"
      />
      <!-- プレイヤーの次の手表示（発射台の上） -->
      <image
        :x="launcherCenterX - 25"
        :y="launcherCenterY - 45"
        width="50"
        height="50"
        :href="colorToSvg(nextBall)"
      />
      <!-- 相手の発射台 -->
      <rect v-if="opponentConnected"
        :x="opponentLauncherCenterX - 30"
        :y="opponentLauncherCenterY - 10"
        width="60"
        height="20"
        fill="#90caf9"
        stroke="#42a5f5"
        stroke-width="3"
      />
      <!-- 相手の次の手表示（発射台の下） -->
      <image v-if="opponentConnected"
        :x="opponentLauncherCenterX - 25"
        :y="opponentLauncherCenterY + 20"
        width="50"
        height="50"
        :href="colorToSvg(opponentNextBall)"
      />
    </svg>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import guSvg from '../assets/image/gu.svg';
import chokiSvg from '../assets/image/choki.svg';
import paSvg from '../assets/image/pa.svg';
import { JankenHand } from '@/constants/jankenHands';

// ボール色コード→SVGファイル
function colorToSvg(c) {
  if (c === JankenHand.ROCK) return guSvg;     // グー
  if (c === JankenHand.SCISSORS) return chokiSvg;  // チョキ
  if (c === JankenHand.PAPER) return paSvg;     // パー
  return guSvg; // デフォルト
}

const props = defineProps({
  board: {
    type: Object,
    required: true
  },
  svgWidth: {
    type: Number,
    default: 400
  },
  svgHeight: {
    type: Number,
    default: 800
  },
  // launcherXを直接propsとして受け取る（論理座標0-100）
  launcherX: {
    type: Number,
    default: 50
  },
  // 相手の発射台の位置（論理座標0-100）
  opponentLauncherX: {
    type: Number,
    default: 50
  },
  // 相手が接続されているかどうか
  opponentConnected: {
    type: Boolean,
    default: false
  },
  // プレイヤーの次の手（最初の1つを表示用）
  nextBall: {
    type: String,
    default: JankenHand.ROCK
  },
  // 相手の次の手（最初の1つを表示用）
  opponentNextBall: {
    type: String,
    default: JankenHand.ROCK
  }
});

// SVGの表示サイズ（px）
const svgWidth = computed(() => props.svgWidth);
const svgHeight = computed(() => props.svgHeight);

// 発射台の座標（論理座標を画面座標に変換）
const launcherCenterX = computed(() => toScreenX(props.launcherX));
const launcherCenterY = computed(() => svgHeight.value - 50); // 少し上に

// 相手の発射台の座標（上下反転で上部に表示）
const opponentLauncherCenterX = computed(() => toScreenX(props.opponentLauncherX));
const opponentLauncherCenterY = computed(() => 50); // 上部に表示

function toScreenX(x) {
  return x * (svgWidth.value - 1) / 100;
}
function toScreenY(y) {
  return y * (svgHeight.value - 1) / 200;
}
</script>

<style src="../assets/css/board.css" scoped></style>