<template>
  <div v-if="show" class="victory-overlay" @click="$emit('close')">
    <div class="confetti-container">
      <div v-for="(_, i) in CONFETTI_COUNT" :key="i" class="confetti" :style="getConfettiStyle(i)"></div>
    </div>
    <div class="victory-modal" @click.stop>
      <div class="victory-content" :class="resultClass">
        <div class="victory-icon">{{ resultIcon }}</div>
        <div class="victory-title">{{ resultTitle }}</div>
        <div class="victory-score">
          <div class="score-line">あなた: <span class="score-value">{{ playerScore }}</span></div>
          <div class="score-line">相手: <span class="score-value">{{ opponentScore }}</span></div>
        </div>
        <div class="victory-message">{{ resultMessage }}</div>
        <button class="close-button" @click="$emit('close')">閉じる</button>
      </div>
    </div>
  </div>
</template>

<script>
// Confetti animation constants (module-level)
const CONFETTI_COLORS = Object.freeze(['#ff6b6b', '#4ecdc4', '#45b7d1', '#f7b731', '#5f27cd', '#00d2d3', '#ff9ff3', '#54a0ff'])
const CONFETTI_COUNT = 100
const MAX_ANIMATION_DELAY = 3
const MIN_ANIMATION_DURATION = 3
const MAX_ANIMATION_DURATION_RANGE = 2
const MIN_CONFETTI_SIZE = 8
const MAX_CONFETTI_SIZE_RANGE = 8

// Pre-generate and freeze confetti styles to avoid recalculation on re-renders
const confettiStyles = Object.freeze(
  Array.from({ length: CONFETTI_COUNT }, (_, index) => {
    const color = CONFETTI_COLORS[index % CONFETTI_COLORS.length]
    const left = Math.random() * 100
    const animationDelay = Math.random() * MAX_ANIMATION_DELAY
    const animationDuration = MIN_ANIMATION_DURATION + Math.random() * MAX_ANIMATION_DURATION_RANGE
    const size = MIN_CONFETTI_SIZE + Math.random() * MAX_CONFETTI_SIZE_RANGE

    return Object.freeze({
      left: `${left}%`,
      backgroundColor: color,
      animationDelay: `${animationDelay}s`,
      animationDuration: `${animationDuration}s`,
      width: `${size}px`,
      height: `${size}px`,
    })
  })
)
</script>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  },
  playerScore: {
    type: Number,
    default: 0
  },
  opponentScore: {
    type: Number,
    default: 0
  },
  isOpponentDisconnect: {
    type: Boolean,
    default: false
  }
})

defineEmits(['close'])

const resultType = computed(() => {
  if (props.isOpponentDisconnect) return 'win'    // 相手の切断は勝利扱い
  if (props.playerScore > props.opponentScore) return 'win'
  if (props.playerScore < props.opponentScore) return 'lose'
  return 'draw'
})

const resultClass = computed(() => `result-${resultType.value}`)

const resultIcon = computed(() => {
  switch (resultType.value) {
    case 'win': return '🎉'
    case 'lose': return '😢'
    case 'draw': return '🤝'
    default: return ''
  }
})

const resultTitle = computed(() => {
  switch (resultType.value) {
    case 'win': return 'YOU WIN!!'
    case 'lose': return 'YOU LOSE...'
    case 'draw': return 'DRAW'
    default: return ''
  }
})

const resultMessage = computed(() => {
  if (props.isOpponentDisconnect) {
    return '相手が切断しました'
  }
  switch (resultType.value) {
    case 'win': return 'おめでとうございます！'
    case 'lose': return '次は頑張りましょう！'
    case 'draw': return 'いい勝負でした！'
    default: return ''
  }
})

function getConfettiStyle(index) {
  // v-for with (_, i) provides index 0-99
  return confettiStyles[index]
}
</script>

<style src="../assets/css/victory-effect.css" scoped></style>
