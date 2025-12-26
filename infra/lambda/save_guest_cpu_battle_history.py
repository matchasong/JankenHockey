import json
import logging
import os
import uuid
from datetime import datetime, timezone

from repositories import GameHistoryRepository

game_history_repository = GameHistoryRepository()

# Response headers
RESPONSE_HEADERS = {"Content-Type": "application/json"}

# 定数
GUEST_USERNAME = "ゲスト"

# logger setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    force=True,
)
logger = logging.getLogger(__name__)


def handler(event, context):
    """handler
    Lambda関数(JankenHockeySaveCpuBattleHistoryFunction)のhandler
    未ログインのユーザーによるCPU対戦が終了したタイミングで、API Gateway経由で呼び出される。
    ゲーム結果をGameHistoryテーブルに保存する。

    save_guest_cpu_battle_history.pyとの違いは、認証情報の取得の有無。

    Args:
        event (dict): lambdaイベント
        context (dict): lambdaコンテキスト

    Returns:
        dict: HTTPレスポンス(結果メッセージ)
    """
    logger.info(f"START {os.path.basename(__file__)}")
    logger.debug(f"event: {event}")

    try:
        # Parse request body
        body = json.loads(event.get("body", "{}"))
        player_score = int(body.get("playerScore", 0))
        cpu_score = int(body.get("cpuScore", 0))

        logger.info(
            f"Guest CPU battle history save - Player: {GUEST_USERNAME}, Player Score: {player_score}, CPU Score: {cpu_score}"
        )

        # Generate unique game history ID for guest CPU battles
        game_history_id = f"guest_cpu_battle_{uuid.uuid4()}"
        current_time = datetime.now(timezone.utc).isoformat()

        # Create game history record
        game_history_record = {
            "id": game_history_id,
            "room_id": game_history_id,  # Use same as ID for CPU battles
            "player1_name": GUEST_USERNAME,
            "player2_name": "CPU",
            "player1_score": player_score,
            "player2_score": cpu_score,
            "end_time": current_time,
            "end_reason": "time_limit",
            "game_type": "guest_cpu_battle",  # Mark as guest CPU battle
        }

        # Save to DynamoDB
        game_history_repository.create_game_history(
            game_history_record=game_history_record
        )

        logger.info(
            f"Guest CPU battle history saved successfully: {game_history_record}"
        )

        logger.info(f"END {os.path.basename(__file__)}")

        return {
            "statusCode": 200,
            "headers": RESPONSE_HEADERS,
            "body": json.dumps(
                {
                    "message": "Guest CPU battle history saved successfully",
                    "gameHistoryId": game_history_id,
                }
            ),
        }

    except Exception as e:
        logger.error(f"Error saving guest CPU battle history: {e}")
        return {
            "statusCode": 500,
            "headers": RESPONSE_HEADERS,
            "body": json.dumps({"error": "Failed to save guest CPU battle history"}),
        }
