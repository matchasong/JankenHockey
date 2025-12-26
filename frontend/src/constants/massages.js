export const MESSAGES = {
    INFO: {
        WAIT_FOR_OPPONENT: '対戦相手を待っています',
        IN_GAME: '対戦中です\n左右ボタンで移動します\n手は自動発射\n上部で得点！',
        OPPONENT_CANCELLED: '相手が切断しました\nあなたの勝ちです！',
        GAME_CANCELLED: 'ゲームを中止しました',
        WIN: (myPoint, opponentPoint) => `あなたの勝ちです！！\nあなた:${myPoint}\n相手:${opponentPoint}`,
        LOSE: (myPoint, opponentPoint) => `あなたの負けです.....\nあなた:${myPoint}\n相手:${opponentPoint}`,
        DRAW: (myPoint, opponentPoint) => `引き分けです。\nあなた:${myPoint}\n相手:${opponentPoint}`
    }
};