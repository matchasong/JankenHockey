import json
import logging
import os
import time
import uuid

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
    """
    Lambda関数(JankenHockeyCreateRoomFunction)のhandler
    ルーム作成時に、Cognitoオーソライザーで認証済みのリクエストについて、API Gateway経由で呼び出される。
    ルーム情報をRoomテーブルに登録する。

    Args:
        event (dict): lambdaイベント
        context (dict): lambdaコンテキスト

    Returns:
        dict: HTTPレスポンス(room_idが入った結果メッセージ)
    """

    logger.info(f"START {os.path.basename(__file__)}")
    logger.debug(f"event: {event}")

    logger.info("Processing create room request")

    try:
        body = json.loads(event.get("body", "{}"))
        creatorName = body.get("creatorName", "")
        message = body.get("message", "")
        room_id = str(uuid.uuid4())

        # Calculate TTL timestamp (24 hours from now)
        expires_at = int(time.time()) + 86400  # 24 hours = 86400 seconds

        item = {
            "id": room_id,
            "creatorName": creatorName,
            "message": message,
            "joined": False,
            "accessible": True,
            "creatorConnectionId": None,  # Will be set when creator connects to WebSocket
            "expires_at": expires_at,
            "player1_name": creatorName,
            "player1_score": 0,
            "player2_name": None,
            "player2_score": 0,
        }

        logger.debug(f"Creating room item: {item}")

        room_repository.create_room(item)

        logger.info(f"Room created with ID: {room_id}")
        logger.info(f"END {os.path.basename(__file__)}")

        return {
            "statusCode": 200,
            "headers": RESPONSE_HEADERS,
            "body": json.dumps({"roomId": room_id, "message": "Room created"}),
        }
    except Exception as e:
        logger.error(f"Error creating room: {e}")
        return {
            "statusCode": 500,
            "headers": RESPONSE_HEADERS,
            "body": json.dumps({"error": str(e)}),
        }
