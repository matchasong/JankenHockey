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
    Lambda関数(JankenHockeyGetRoomsFunction)のhandler
    ルーム一覧画面を表示する際に、Cognitoオーソライザーで認証済みのリクエストについて、API Gateway経由で呼び出される。
    参加可能なルームのリストを取得して返す。

    Args:
        event (dict): lambdaイベント
        context (dict): lambdaコンテキスト

    Returns:
        dict: HTTPレスポンス(roomのリスト)
    """
    logger.info(f"START {os.path.basename(__file__)}")
    logger.debug(f"event: {event}")

    # アクセス可能なルームを取得
    logger.info("Fetching accessible rooms from Room table")
    rooms = room_repository.get_accessible_rooms()
    logger.debug(f"Fetched rooms: {rooms}")

    # 自分のプレイヤー名を取得
    player_name = event["requestContext"]["authorizer"]["claims"]["cognito:username"]
    logger.debug(f"Player name from token: {player_name}")

    # 表示対象のルームリストを作成
    result = []
    for room in rooms:
        if room.get("creatorName") == player_name:
            # 自分が作成したルームは表示しない
            continue
        else:
            # 自分が作成していないルームは表示対象結果リストに追加
            result.append(
                {
                    "roomId": room.get("id"),
                    "creatorName": room.get("creatorName", ""),
                    "creatorId": room.get("creatorId", ""),
                    "message": room.get("message", ""),
                    "joined": room.get("joined", False),
                }
            )

    logger.info("Fetched room list successfully")
    logger.debug(f"Room list result: {result}")

    logger.info(f"END {os.path.basename(__file__)}")

    return {
        "statusCode": 200,
        "headers": RESPONSE_HEADERS,
        "body": json.dumps({"rooms": result}),
    }
