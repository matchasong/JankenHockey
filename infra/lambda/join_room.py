import json
import logging
import os

from repositories import RoomRepository

# Dynamodbに接続
room_repository = RoomRepository()

# Response headers
RESPONSE_HEADERS = {"Content-Type": "application/json"}

# logger setup
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    force=True,
)
logger = logging.getLogger(__name__)


def handler(event, context):
    """handler
    Lambda関数(JankenHockeyJoinRoomFunction)のhandler
    ルーム一覧画面で参加するルームを選択すると、Cognitoオーソライザーで認証済みのリクエストについて、API Gateway経由で呼び出される。
    ルームテーブルのjoined項目を更新し、ルームに参加する。

    Args:
        event (dict): lambdaイベント
        context (dict): lambdaコンテキスト

    Returns:
        dict: HTTPレスポンス(結果メッセージ)
    """

    logger.info(f"START {os.path.basename(__file__)}")
    logger.debug(f"event: {event}")

    try:
        body = json.loads(event.get("body", "{}"))
        room_id = body.get("roomId", "")
        player_name = body.get("playerName")

        # 競合がない場合に限り、ルームに参加
        room_repository.join_room_conditional(room_id=room_id, player_name=player_name)

        logger.info(
            f"Joined room successfully: roomId={room_id}, playerName={player_name}"
        )

        logger.info(f"END {os.path.basename(__file__)}")

        return {
            "statusCode": 200,
            "headers": RESPONSE_HEADERS,
            "body": json.dumps(
                {"roomId": room_id, "message": "Joined room", "joined": True}
            ),
        }
    except Exception as e:
        logger.error(f"Failed to join room: {e}")
        return {
            "statusCode": 500,
            "headers": RESPONSE_HEADERS,
            "body": json.dumps({"error": str(e)}),
        }
