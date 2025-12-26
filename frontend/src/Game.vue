<script setup>
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Board from './components/Board.vue'
import VictoryEffect from './components/VictoryEffect.vue'
import guSvg from './assets/image/gu.svg'
import chokiSvg from './assets/image/choki.svg'
import paSvg from './assets/image/pa.svg'
import { createGameSocket } from '@/api/socket'
import { isAuthenticated } from '@/utils/auth'
import { saveCpuBattleHistory, saveGuestCpuBattleHistory } from '@/api/gameHistory'
import { JankenHand, JANKEN_HANDS } from '@/constants/jankenHands'
import { MESSAGES } from '@/constants/massages'

// ルートクエリパラメータを取得
const route = useRoute()
const router = useRouter()

const roomId = route.query.roomId
const playerName = route.query.playerName

// 終了条件 - 1分間の時間制
const matchDuration = 60; // 60秒間のマッチ

// 得点設定
const GOAL_POINTS = 1; // ゴールした時の得点

// 発射台の位置・発射パワー
const launcherX = ref(50); // 論理座標で中央（0-100）
const launcherY = 190; // 盤面下部（ボール半径分上）
const minX = 10; // 左端
const maxX = 90; // 右端
const moveStep = 2; // 1フレームごとの移動量

// 相手の発射台の位置
const opponentLauncherX = ref(50); // 論理座標で中央（0-100）

// ゲーム設定
const message = ref(MESSAGES.INFO.WAIT_FOR_OPPONENT); // ユーザーメッセージ
const onGame = ref(false); // ゲーム開始フラグ

// マッチング待機タイムアウト関連
const showTimeoutPopup = ref(false);
let matchingTimeout = null;

// ゲーム時間管理
const gameTimeRemaining = ref(matchDuration); // 残り時間（秒）
let gameTimer = null; // ゲームタイマーのID

// CPU対戦フラグ
const isCpuBattle = ref(route.query.isCpuBattle === 'true' || route.query.cpu === 'true');

// 次のじゃんけんをランダムに選ぶ関数
function randomBallColor() {
  return JANKEN_HANDS[Math.floor(Math.random() * JANKEN_HANDS.length)];
}

// ボールコードからSVGファイルを取得する関数
function colorToSvg(c) {
  if (c === JankenHand.ROCK) return guSvg;     // グー
  if (c === JankenHand.SCISSORS) return chokiSvg;  // チョキ
  if (c === JankenHand.PAPER) return paSvg;     // パー
}

// 自分の次のボール
const nextBalls = ref([
  randomBallColor(),
  randomBallColor(),
  randomBallColor()
]);

// 相手の次のボール
const opponentNextBalls = ref([]);

// プレイヤー得点変数
const me = ref({
  name: playerName,
  point: 0
});

const opponent = ref({
    name: '',
    point: 0
});

const board = ref({ balls: [] }); // 盤面情報（ボール配列）

// ゲーム中止関連
const showCancelConfirm = ref(false);
const opponentConnected = ref(false);

// 勝利エフェクト表示フラグ
const showVictoryEffect = ref(false);
const isOpponentDisconnect = ref(false);

// ゲーム終了フラグ
const isGameEnded = computed(() => {
  return gameTimeRemaining.value <= 0;
});

// 連続移動制御用
let leftPressed = false;
let rightPressed = false;
let moveAnimationId = null;

// マウスボタン用の移動制御
function handleLeftButtonDown() {
  if (!leftPressed) {
    leftPressed = true;
    if (!moveAnimationId) {
      moveLauncher();
    }
  }
}

function handleRightButtonDown() {
  if (!rightPressed) {
    rightPressed = true;
    if (!moveAnimationId) {
      moveLauncher();
    }
  }
}

function handleLeftButtonUp() {
  leftPressed = false;
  if (!leftPressed && !rightPressed && moveAnimationId) {
    cancelAnimationFrame(moveAnimationId);
    moveAnimationId = null;
  }
}

function handleRightButtonUp() {
  rightPressed = false;
  if (!leftPressed && !rightPressed && moveAnimationId) {
    cancelAnimationFrame(moveAnimationId);
    moveAnimationId = null;
  }
}

// キーボード用の移動制御
function handleKeydown(e) {
  if (e.code === 'ArrowLeft') {
    if (!leftPressed) {
      leftPressed = true;
      if (!moveAnimationId) {
        moveLauncher();
      }
    }
  } else if (e.code === 'ArrowRight') {
    if (!rightPressed) {
      rightPressed = true;
      if (!moveAnimationId) {
        moveLauncher();
      }
    }
  }
}

function handleKeyup(e) {
  if (e.code === 'ArrowLeft') {
    leftPressed = false;
    if (!leftPressed && !rightPressed && moveAnimationId) {
      cancelAnimationFrame(moveAnimationId);
      moveAnimationId = null;
    }
  } else if (e.code === 'ArrowRight') {
    rightPressed = false;
    if (!leftPressed && !rightPressed && moveAnimationId) {
      cancelAnimationFrame(moveAnimationId);
      moveAnimationId = null;
    }
  }
}

// 左右ボタン/キーが押されているか否かの状態によって、自分の発射台を動かすループ処理
function moveLauncher() {
  const prevX = launcherX.value;

  if (leftPressed) {
    launcherX.value = Math.max(minX, launcherX.value - moveStep);
  }
  if (rightPressed) {
    launcherX.value = Math.min(maxX, launcherX.value + moveStep);
  }

  // 位置が変わった場合、相手に送信（CPU対戦時は送信しない）
  if (launcherX.value !== prevX && !isCpuBattle.value) {
    sendLauncherPositionEvent();
  }

  if (leftPressed || rightPressed) {
    moveAnimationId = requestAnimationFrame(moveLauncher);
  } else {
    moveAnimationId = null;
  }
}

// ボール発射のループ処理
const autoFireInterval = 1000; //ms換算
const delayToNextBoundary = 0;
let autoFireTimer = null;
let isAutoFireStarted = false;

function startAutoFire() {
  if (isAutoFireStarted) {
    // 既に開始している場合は何もしない
    return;
  }

  isAutoFireStarted = true;

  setTimeout(() => {
    // 定期的な発射タイマーを開始
    autoFireTimer = setInterval(() => {
      fireBall();
    }, autoFireInterval);
  }, delayToNextBoundary);
}

function stopAutoFire() {
  if (autoFireTimer) {
    clearInterval(autoFireTimer);
    autoFireTimer = null;
  }
}

// ボール発射
function fireBall() {
  if(isGameEnded.value){
    return; // ゲーム終了後は発射しない
  }

  // 真上に発射
  const vx = 0; // 水平速度は0（真上）
  const vy = -ballSpeed; // 垂直速度（上向きなので負）

  const id = 'ball-' + me.value.name + Date.now() + '-' + Math.floor(Math.random() * 10000);
  // 発射するボールの色は nextBalls[0]
  const color = nextBalls.value[0];

  const newBall = {
    id,
    player: 'me',
    x: launcherX.value,
    y: launcherY,
    vx,
    vy,
    color
  };
  board.value.balls.push(newBall);

  // 発射時にボール情報を相手に送信
  sendBallEvent(newBall);
  // nextBallsを1つ進めて新しい色を追加
  nextBalls.value.shift();
  nextBalls.value.push(randomBallColor());
  // 次の手の情報を相手に送信
  sendNextHandsEvent();
}

// トップページに戻る
function returnToTop() {
  // WebSocket接続をクリーンアップしてからページ遷移
  if (socket && socket.readyState !== WebSocket.CLOSED) {
    socket.close();
    socket = null;
  }
  router.push({ name: 'TopView' });
}

// ゲーム中止関連の関数
function showCancelConfirmation() {
  if (isGameEnded.value) {
    return; // ゲーム終了後は中止できない
  }
  showCancelConfirm.value = true;
}

function cancelGame() {
  showCancelConfirm.value = false;
  sendCancelEvent();
  stopGameTimer();
  // CPU対戦中の場合はCPUの動きを停止（結果表示はスキップ）
  if (isCpuBattle.value) {
    handleCpuBattleCancel();
  }

  message.value = MESSAGES.INFO.GAME_CANCELLED;

  // 1秒後にトップ画面に戻る
  setTimeout(() => {
    returnToTop();
  }, 1000);
}

function closeCancelConfirm() {
  showCancelConfirm.value = false;
}

// マッチング待機タイムアウト処理
function startMatchingTimeout() {
  // 1分（60000ms）後にタイムアウト
  matchingTimeout = setTimeout(() => {
    if (!opponentConnected.value) {
      showTimeoutPopup.value = true;
    }
  }, 60000);
}

function clearMatchingTimeout() {
  if (matchingTimeout) {
    clearTimeout(matchingTimeout);
    matchingTimeout = null;
  }
}

// ゲームタイマー管理
function startGameTimer() {
  if (gameTimer) return; // 既に開始している場合は何もしない

  gameTimer = setInterval(() => {
    if (gameTimeRemaining.value > 0) {
      gameTimeRemaining.value--;
    }
  }, 1000);
}

function stopGameTimer() {
  if (gameTimer) {
    clearInterval(gameTimer);
    gameTimer = null;
  }

  // ゲーム終了時に自動発射も停止
  stopAutoFire();
}

// 時間を MM:SS 形式でフォーマット、またはゲーム終了時は「ゲーム終了」を表示
const formattedTime = computed(() => {
  if (isGameEnded.value) {
    return "ゲーム終了";
  }
  const minutes = Math.floor(gameTimeRemaining.value / 60);
  const remainingSeconds = gameTimeRemaining.value % 60;
  return `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
});

function handleTimeoutConfirm() {
  showTimeoutPopup.value = false;
  // WebSocket接続をクリーンアップしてからページ遷移
  if (socket && socket.readyState !== WebSocket.CLOSED) {
    socket.close();
    socket = null;
  }
  returnToTop();
}

function handleCpuBattleCancel() {
  // CPU対戦中止時にCPUの動きを停止（結果表示はスキップ）
  stopCpuMoveLoop();
  stopCpuAutoFire();
}

async function handleCpuBattleTimeout() {
  stopGameTimer();

  // CPU対戦終了時にCPUの動きを停止
  stopCpuMoveLoop();
  stopCpuAutoFire();

  // CPU対戦の結果を表示（自分の点数とCPUの点数)
  showResultMessage(me.value.point, opponent.value.point);

  // CPU対戦の結果をゲーム履歴に保存
  // ログイン済みユーザーは認証付きAPI、ゲストユーザーは認証なしAPIを使用
  try {
    if (isAuthenticated()) {
      await saveCpuBattleHistory({
        playerScore: me.value.point,
        cpuScore: opponent.value.point
      });
    } else {
      await saveGuestCpuBattleHistory({
        playerScore: me.value.point,
        cpuScore: opponent.value.point
      });
    }
  } catch (error) {
    // ゲーム履歴の保存に失敗してもゲーム終了の表示は続行する
    console.error("Failed to save CPU battle history");
  }
}

// 盤面サイズ（可変対応）
const boardWidth = ref(400);
const boardHeight = ref(800);

// ボールスピード
const ballSpeed = 1.5;

let animationFrameId = null;
function updateBalls() {
  // 盤面サイズ
  const maxY = 200;

  // Board.vueのボール半径を1.5倍に調整（25.6 * 1.5 / 2 = 19.2）
  const ballRadiusPx = 19.2;
  const strokeWidth = 4;
  const scaleX = 400 / 100;
  const scaleY = 800 / 200;
  const ballRadiusX = (ballRadiusPx + strokeWidth / 2) / scaleX;
  const ballRadiusY = (ballRadiusPx + strokeWidth / 2) / scaleY;

  // 各ボールの位置・速度を更新
  // まず全ボールの新しい位置・速度を計算
  let newBalls = board.value.balls.map(ball => {
    // ゲーム終了時の早期リターン
    if (isGameEnded.value) {
        return { ...ball }; // ゲーム終了後は得点しない
    }

    // ボールの位置更新
    let x = ball.x + ball.vx
    let y = ball.y + ball.vy

    // ボールの速度更新
    let vx = ball.vx;
    let vy = ball.vy;

    if (y < ballRadiusY) {
      // 上側の境界に当たったら自分の得点
      // ゲーム終了前のみ
      if(isCpuBattle.value){
        // CPU対戦の場合のみ、得点加算。(pvp対戦はWebSocket経由で得点イベントを受け取る)
        me.value.point += GOAL_POINTS;
      }
      // 自分の得点イベントを発行する
      const removedBall = { ...ball, x, y, vx, vy };
      sendPointEvent(me.value.name, GOAL_POINTS, removedBall.id);

      // ボールを消す
      return null;
    }
    if (y > maxY - ballRadiusY) {
      // 下側の境界に当たったら相手の得点
      if(isCpuBattle.value){
        // CPU対戦の場合のみ、得点加算。(pvp対戦はWebSocket経由で得点イベントを受け取る)
        opponent.value.point += GOAL_POINTS;
      }

      // ボールを消す
      return null;
    }
    return { ...ball, x, y, vx, vy };
  });

  // nullを除外してから衝突判定
  newBalls = newBalls.filter(b => b !== null);
  // じゃんけんルール判定関数
  function getJankenResult(color1, color2) {
    // rock = グー, scissors = チョキ, paper = パー
    if (color1 === color2) return 'draw'; // あいこ
    if (color1 === JankenHand.ROCK && color2 === JankenHand.SCISSORS) return 'win1'; // グー vs チョキ = グーの勝ち
    if (color1 === JankenHand.SCISSORS && color2 === JankenHand.PAPER) return 'win1'; // チョキ vs パー = チョキの勝ち
    if (color1 === JankenHand.PAPER && color2 === JankenHand.ROCK) return 'win1'; // パー vs グー = パーの勝ち
    return 'win2'; // それ以外は color2 の勝ち
  }

  // ボール同士の衝突判定とじゃんけんルール適用
  const ballsToRemove = new Set(); // 削除対象のボールのインデックス
  for (let i = 0; i < newBalls.length; i++) {
    if (ballsToRemove.has(i)) continue; // 既に削除対象のボールはスキップ
    for (let j = i + 1; j < newBalls.length; j++) {
      if (ballsToRemove.has(j)) continue; // 既に削除対象のボールはスキップ
      const b1 = newBalls[i];
      const b2 = newBalls[j];
      const dx = b1.x - b2.x;
      const dy = b1.y - b2.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      // 衝突判定（中心間距離が半径の和以下）
      if (dist < ballRadiusX * 2) {
        const jankenResult = getJankenResult(b1.color, b2.color);
        if (jankenResult === 'draw') {
          // あいこの場合は両方とも消える
          ballsToRemove.add(i);
          ballsToRemove.add(j);
        } else if (jankenResult === 'win1') {
          // b1の勝ち、b2を削除
          ballsToRemove.add(j);
        } else {
          // b2の勝ち、b1を削除
          ballsToRemove.add(i);
        }
      }
    }
  }

  // 削除対象のボールを除外
  newBalls = newBalls.filter((_, index) => !ballsToRemove.has(index));
  // 盤面を更新
  board.value.balls = newBalls;

  // ゲーム終了時はアニメーションループを継続しない
  if (!isGameEnded.value) {
    animationFrameId = requestAnimationFrame(updateBalls);
  }
}

function setUpGame(opponentName) {
  if (onGame.value) {  // ゲーム開始済みの場合は無視
    return;
  }
  // 相手の名前を設定
  opponent.value.name = opponentName

  // ゲーム状態のフラグを更新
  opponentConnected.value = true;
  onGame.value = true;

  // メッセージを更新
  message.value = MESSAGES.INFO.IN_GAME;

  // マッチング待機タイムアウトをクリア
  clearMatchingTimeout();

  // ゲーム開始時に自分の次の手を送信
  sendNextHandsEvent();

  // ゲームタイマーを開始
  startGameTimer();

  // 自動発射を開始
  startAutoFire();
}

let socket = null;

function setupSocket() {
  socket = createGameSocket({
    onOpen: function() {
      // マッチング待機タイムアウトを開始
      startMatchingTimeout();
      message.value = MESSAGES.INFO.WAIT_FOR_OPPONENT;

      // 接続したら必ずwaitイベントを送信
      sendWaitEvent();
    },
    onMessage: function(e) {
      let parsedData;
      try {
        parsedData = JSON.parse(e.data);
      } catch (err) {
        console.error('onMessage: JSON parse error');
        return;
      }
      switch (parsedData.type) {
        case "start":
            if(onGame.value){ // ゲーム開始済みの場合は無視
              return;
            }

            // サーバーから両方のプレイヤー名を受け取る
            const creatorName = parsedData.data.creatorName;
            const joinerName = parsedData.data.joinerName;

            // 相手の名前を決定
            const opponentName = (me.value.name === creatorName) ? joinerName : creatorName;

            // 開始処理
            setUpGame(opponentName);
            break;
        case "game_timeout":

            // 受け取ったタイムアウトイベントで、ローカルのイベントの結果を更新
            parsedData.data.player1_name === me.value.name ? me.value.point = parsedData.data.player1_score : opponent.value.point = parsedData.data.player1_score;
            parsedData.data.player2_name === me.value.name ? me.value.point = parsedData.data.player2_score : opponent.value.point = parsedData.data.player2_score;

            // 終了処理
            gameTimeRemaining.value = 0; // タイマーを0にして「ゲーム終了」を表示
            stopGameTimer(); // タイマーを停止
            showResultMessage(me.value.point, opponent.value.point);
            isGameEnded.value = true;

            break;
        case "point":
            if (isGameEnded.value) {
              // ゲーム終了後は得点イベントを反映しない
              break;
            }
            if (parsedData.data) {
                if (parsedData.data.player === me.value.name) {
                  // 自分が得点した場合
                  me.value.point += Number(parsedData.data.point);
                } else if (parsedData.data.player === opponent.value.name) {
                  // 相手が得点した場合
                  opponent.value.point += Number(parsedData.data.point);
                }
            }
            break;
        case "cancel":
            if (isGameEnded.value) {
              // ゲーム終了後は中止イベントを反映しない
              break;
            }
            if (parsedData.data && parsedData.data.player === opponent.value.name) {
              // 対戦相手が中止した場合
              stopGameTimer(); // タイマーを停止
              gameTimeRemaining.value = 0; // タイマーを0にして「ゲーム終了」を表示

              // 相手の切断は、自分の勝利として扱う（現在のスコアのまま、勝利ポップアップを表示）
              isOpponentDisconnect.value = true;

              showResultMessage(me.value.point, opponent.value.point, true);
              isGameEnded.value = true;
              opponentConnected.value = false;
            }
            break;
        case "ball":
            if (isGameEnded.value){
                break;
            }
            if (!onGame.value) {
                return; // ゲームが始まっていない場合は無視
            }
            if (!parsedData.data || !parsedData.data.player) {
                return; // プレイヤー情報がない場合は無視
            }
            if (parsedData.data.player !== me.value.name && parsedData.data.player !== opponent.value.name) {
                return; // 不明なプレイヤーのボールは無視
            }
            if (parsedData.data.player === me.value.name) {
                return; // 自分のボールは無視
            }

            // 相手からボール1個分の情報が来た場合に、画面に反映する
            if (parsedData.data && parsedData.data.ball) {
                const b = parsedData.data.ball;
                // 相手のボールなら盤面に追加
                // 上下反転: xはそのまま, yは maxY(200) - y
                const maxY = 200;
                const flippedBall = {
                    ...b,
                    x: b.x,
                    y: maxY - b.y,
                    vx: b.vx,
                    vy: -b.vy, // 速度も上下反転
                    player: 'opponent'
                };
                board.value.balls.push(flippedBall);
            }
            break;
        case "next_hands":
            if(isGameEnded.value){
                break;
            }
            if (!parsedData.data || !parsedData.data.player) {
                return;
            }
            if (parsedData.data.player === me.value.name) {
                return;
            }
            if (parsedData.data.player === opponent.value.name && parsedData.data.nextBalls) {
                opponentNextBalls.value = parsedData.data.nextBalls;
            }
            break;
        case "launcher_position":
            if(isGameEnded.value){
                break;
            }
            if (!parsedData.data || !parsedData.data.player) {
                return;
            }
            if (parsedData.data.player === me.value.name) {
                return;
            }
            if (parsedData.data.player === opponent.value.name) {
                opponentLauncherX.value = parsedData.data.launcherX;
            }
            break;
      }
    },
    onError: function(error) {
      console.error('[WebSocket] Error occurred:', error);
    },
    roomId: roomId, // ルームIDを送信
    isRoomCreator: route.query.isRoomCreator === "true" // ルーム作成者かどうか
  });
}

// ゲーム結果メッセージ表示
function showResultMessage(myPoint, opponentPoint, cancelled = false) {

  if (cancelled) {
    message.value = MESSAGES.INFO.GAME_CANCELLED;
    showVictoryEffect.value = true;
    return;
  }

  if (myPoint > opponentPoint) {
    message.value = MESSAGES.INFO.WIN(myPoint, opponentPoint);
  } else if (myPoint < opponentPoint) {
    message.value = MESSAGES.INFO.LOSE(myPoint, opponentPoint);
  } else {
    message.value = MESSAGES.INFO.DRAW(myPoint, opponentPoint);
  }

  // 勝利エフェクトを表示
  showVictoryEffect.value = true;
}

// 勝利エフェクトを閉じる
function closeVictoryEffect() {
  showVictoryEffect.value = false;
  isOpponentDisconnect.value = false;
}

function sendWaitEvent() {
  if(isCpuBattle.value){
    return; // CPU対戦中は送信しない
  }
  if (socket) {
    socket.send(JSON.stringify({
      action: "default",
      data: {
        type: "wait",
        player: me.value.name
      }
    }));
  }
}

function sendBallEvent(ball) {
  if(isCpuBattle.value){
    return; // CPU対戦中は送信しない
  }
  if (isGameEnded.value) {
    return; // ゲーム終了後はイベントを送信しない
  }
  if (socket) {
    socket.send(JSON.stringify({
      action: "default",
      data: {
        type: "ball",
        player: me.value.name,
        ball: ball
      }
    }));
  }
}

function sendNextHandsEvent() {
  if(isCpuBattle.value){
    return; // CPU対戦中は送信しない
  }
  if (isGameEnded.value) {
    return; // ゲーム終了後はイベントを送信しない
  }
  if (socket) {
    socket.send(JSON.stringify({
      action: "default",
      data: {
        type: "next_hands",
        player: me.value.name,
        nextBalls: nextBalls.value
      }
    }));
  }
}

function sendCancelEvent() {
  if(isCpuBattle.value){
    return; // CPU対戦中は送信しない
  }
  if (socket) {
    socket.send(JSON.stringify({
      action: "default",
      data: {
        type: "cancel",
        player: me.value.name
      }
    }));
  }
}

function sendLauncherPositionEvent() {
  if(isCpuBattle.value){
    return; // CPU対戦中は送信しない
  }
  if (isGameEnded.value) {
    return; // ゲーム終了後はイベントを送信しない
  }
  if (socket && opponentConnected.value) {
    socket.send(JSON.stringify({
      action: "default",
      data: {
        type: "launcher_position",
        player: me.value.name,
        launcherX: launcherX.value
      }
    }));
  }
}

function sendPointEvent(playerName, points, ballId) {
  if(isCpuBattle.value){
    return; // CPU対戦中は送信しない
  }
  if (isGameEnded.value) {
    return; // ゲーム終了後は得点イベントを送信しない
  }
  socket.send(JSON.stringify({
    action: "default",
    data: {
      type: "point",
      player: playerName,
      point: points.toString(),
      ball: ballId || ""
    }
  }));
}

// --- CPU用ロジック ---
let cpuMoveTimer = null;
function startCpuMoveLoop() {
  if (cpuMoveTimer) clearInterval(cpuMoveTimer);
  cpuMoveTimer = setInterval(() => {
    // ランダムに左右に移動
    const RawOpponentNextLauncherX = opponentLauncherX.value + (Math.random() - 0.5) * 20; // ボード0から100までに対して、-10から+10の移動幅
    const FixedOpponentNextLauncherX = Math.max(minX, Math.min(maxX, RawOpponentNextLauncherX));
    opponentLauncherX.value = FixedOpponentNextLauncherX
  }, 100); // 100msごとに移動
}

function stopCpuMoveLoop() {
  if (cpuMoveTimer) {
    clearInterval(cpuMoveTimer);
    cpuMoveTimer = null;
  }
}

// --- CPU用自動発射機能 ---
let cpuAutoFireTimer = null;
function startCpuAutoFire() {
  if (cpuAutoFireTimer) {
    clearInterval(cpuAutoFireTimer);
    cpuAutoFireTimer = null;
  }
  // 同期化不要、即時開始
  cpuAutoFireTimer = setInterval(() => {
    if (isGameEnded.value) return;

    // CPUのボール色
    const color = opponentNextBalls.value[0]

    // CPUのボールを作成
    const vx = 0;
    const vy = ballSpeed; // CPUは下向きに発射
    const id = 'cpu-ball-' + Date.now() + '-' + Math.floor(Math.random() * 10000);
    const newBall = {
      id,
      player: 'cpu',
      x: opponentLauncherX.value,
      y: 10, // 盤面上部から発射
      vx,
      vy,
      color
    };
    board.value.balls.push(newBall);
    // opponentNextBallsを1つ進めて新しい色を追加
    opponentNextBalls.value.shift();
    opponentNextBalls.value.push(JANKEN_HANDS[Math.floor(Math.random()*3)]);
  }, autoFireInterval);
}

function stopCpuAutoFire() {
  if (cpuAutoFireTimer) {
    clearInterval(cpuAutoFireTimer);
    cpuAutoFireTimer = null;
  }
}

// CPU対戦終了処理
watch(isGameEnded, () => {
  if (isGameEnded.value && isCpuBattle.value) {
    handleCpuBattleTimeout();
  }
});

// --- CPU用ロジック ここまで---

onMounted(() => {
  if (!isCpuBattle.value){
      setupSocket();
  }
  animationFrameId = requestAnimationFrame(updateBalls);
  window.addEventListener('keydown', handleKeydown);
  window.addEventListener('keyup', handleKeyup);
  if (isCpuBattle.value) {
    opponent.value.name = 'CPU';  // Set opponent name to CPU
    opponentConnected.value = true; // Show CPU launcher
    onGame.value = true; // Start the game
    message.value = MESSAGES.INFO.IN_GAME;
    // Initialize CPU's next balls
    opponentNextBalls.value = [...JANKEN_HANDS];
    // Start game components
    startGameTimer();
    startAutoFire();
    startCpuMoveLoop();
    startCpuAutoFire();
  }
});
onUnmounted(() => {
  if (isCpuBattle.value) {
    stopCpuMoveLoop();
    stopCpuAutoFire();
  }
  if (animationFrameId) cancelAnimationFrame(animationFrameId);
  window.removeEventListener('keydown', handleKeydown);
  window.removeEventListener('keyup', handleKeyup);
  // マッチング待機タイムアウトをクリア
  clearMatchingTimeout();
  // ゲームタイマーをクリア
  stopGameTimer();
  // 自動発射をクリア
  stopAutoFire();

  // WebSocket接続をクリーンアップ
  if (socket && socket.readyState !== WebSocket.CLOSED) {
    socket.close();
    socket = null;
  }

});

</script>

<template>
  <div>
    <!-- 勝利エフェクト -->
    <VictoryEffect
      :show="showVictoryEffect"
      :playerScore="me.point"
      :opponentScore="opponent.point"
      :isOpponentDisconnect="isOpponentDisconnect"
      @close="closeVictoryEffect"
    />

    <!-- マッチング待機タイムアウトポップアップ -->
    <div v-if="showTimeoutPopup" class="modal-overlay">
      <div class="modal-content">
        <div class="modal-title">マッチング待機タイムアウト</div>
        <div class="modal-message">1分間待ってもマッチングできませんでした。<br>トップ画面に戻ります。</div>
        <div class="modal-actions">
          <button @click="handleTimeoutConfirm" class="modal-btn ok">OK</button>
        </div>
      </div>
    </div>

    <!-- ゲーム中止確認ポップアップ -->
    <div v-if="showCancelConfirm" class="modal-overlay cancel-confirm">
      <div class="modal-content">
        <div class="modal-title">ゲーム中止確認</div>
        <div class="modal-message">本当にゲームを中止しますか？<br>中止した場合、あなたの負けとなります。</div>
        <div class="modal-actions button-group">
          <button @click="cancelGame" class="modal-btn cancel-action">中止する</button>
          <button @click="closeCancelConfirm" class="modal-btn cancel-dismiss">キャンセル</button>
        </div>
      </div>
    </div>

    <main>
      <div id="left">
          <Board :board="board"
                 :launcherX="launcherX"
                 :opponentLauncherX="opponentLauncherX"
                 :opponentConnected="opponentConnected"
                 :nextBall="nextBalls[0]"
                 :opponentNextBall="opponentNextBalls[0] || JankenHand.ROCK"
                 :svgWidth="boardWidth" :svgHeight="boardHeight" />
          <div v-if="onGame && !isGameEnded" class="control-buttons">
            <button
              class="move-btn left-btn"
              @mousedown="handleLeftButtonDown"
              @mouseup="handleLeftButtonUp"
              @mouseleave="handleLeftButtonUp"
              @touchstart.prevent="handleLeftButtonDown"
              @touchend.prevent="handleLeftButtonUp"
              @touchcancel.prevent="handleLeftButtonUp"
            >
              ◀
            </button>
            <button
              class="move-btn right-btn"
              @mousedown="handleRightButtonDown"
              @mouseup="handleRightButtonUp"
              @mouseleave="handleRightButtonUp"
              @touchstart.prevent="handleRightButtonDown"
              @touchend.prevent="handleRightButtonUp"
              @touchcancel.prevent="handleRightButtonUp"
            >
              ▶
            </button>
          </div>
      </div>
      <div id="right">
          <div id="game-timer" class="timer-display">
            <div class="timer-text">
              {{ formattedTime }}
            </div>
          </div>
          <div id="right-top" class="player-opponent">
            <template v-if="opponentConnected">
              <span class="player-label">相手</span>
              （{{ opponent.name }}）: {{ opponent.point }}
            </template>
            <template v-else>
              waiting...
            </template>
          </div>
          <div id="right-middle" class="player-self">
            <span class="player-label">あなた</span>
            （{{ me.name }}）: {{ me.point }}
          </div>
          <div id="next-hands">
            <div v-if="opponentConnected && opponentNextBalls.length > 0" class="next-hands-section">
              <div class="next-hands-title">相手の次の手</div>
              <div class="next-hands-container">
                <svg v-for="(c, i) in opponentNextBalls" :key="'opp-' + i" width="60" height="60">
                  <image :x="6" :y="6" width="48" height="48" :href="colorToSvg(c)" />
                </svg>
              </div>
            </div>
            <div v-else-if="opponentConnected" class="next-hands-section">
              <div class="next-hands-title">相手の次の手</div>
              <div class="waiting-message">待機中...</div>
            </div>
            <div>
              <div class="next-hands-title">あなたの次の手</div>
              <div class="next-hands-container">
                <svg v-for="(c, i) in nextBalls" :key="i" width="60" height="60">
                  <image :x="6" :y="6" width="48" height="48" :href="colorToSvg(c)" />
                </svg>
              </div>
            </div>
          </div>
          <div id="right-bottom">{{ message }}</div>
      </div>
      <div id="output"></div>
    </main>
    <!-- OpenMoji License Notice -->
    <div class="license-notice">Icons(Janken hands) designed by<a href="https://openmoji.org/" target="_blank" rel="noopener">OpenMoji</a> – the open-source emoji and icon project. License:
        <a href="https://creativecommons.org/licenses/by-sa/4.0/" target="_blank" rel="noopener">CC BY-SA 4.0</a>
    </div>

    <!-- Cancel Game Button - positioned unobtrusively -->
    <button v-if="!isGameEnded && (onGame || !isCpuBattle)" @click="showCancelConfirmation" class="cancel-game-btn">
      中止
    </button>

    <!-- Return to Top Button -->
    <button v-if="isGameEnded" @click="returnToTop" class="return-to-top-btn">
      トップに戻る
    </button>
  </div>
</template>

<style src="./assets/css/game.css" scoped></style>
