import asyncio
from datetime import datetime, timezone
import json
import logging
import os
import time

import boto3

from repositories import ConnectionRepository, GameHistoryRepository, RoomRepository


# API Gateway Management APIに接続
api_endpoint = os.environ.get("API_ENDPOINT")
stage = os.environ.get("STAGE")
url = f"{api_endpoint}/{stage}".replace("wss", "https")
apigw_management = boto3.client("apigatewaymanagementapi", endpoint_url=f"{url}")

# Dynamodbに接続
room_repository = RoomRepository()
connection_repository = ConnectionRepository()
game_history_repository = GameHistoryRepository()

# ゲームタイムアウト時間（秒）
GAME_TIMEOUT_SECONDS = 60

# logger setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    force=True,
)
logger = logging.getLogger(__name__)


async def async_send_message(post_data, item):
    """
    async_send_message
    WebSocket接続にメッセージを送信
    """
    try:
        await asyncio.to_thread(
            apigw_management.post_to_connection, ConnectionId=item["id"], Data=post_data
        )
        logger.info(f"Message sent to connection {item['id']}")
    except apigw_management.exceptions.GoneException:
        logger.error(
            f"GoneException: connection {item['id']} is gone. Deleting from DynamoDB."
        )
        connection_repository.delete_connection(item["id"])
    except Exception as e:
        logger.error(f"Exception sending message to {item['id']}: {e}")


async def async_main(tasks):
    """
    async_main
    非同期タスクを実行
    """
    await asyncio.gather(*tasks)


def get_winner(player1_score, player2_score, player1_name, player2_name):
    """
    decide_winner
    スコアに基づいて勝者を決定する
    """
    if player1_score > player2_score:
        return player1_name
    elif player2_score > player1_score:
        return player2_name
    else:
        return "draw"


def handler(event, context):
    """
    Lambda関数(JankenHockeyGameTimeoutFunction)のhandler
    ゲーム開始時点でJankenHockeyDefaultFunctionから非同期で呼び出される。
    ゲームタイムアウト時間（60秒）待機した後、ルームに接続している全てのクライアントにタイムアウトメッセージを送信し、
    ゲーム履歴をGameHistoryテーブルに保存する。

    Args:
        event (dict): lambdaイベント
        context (dict): lambdaコンテキスト

    Returns:
        dict: HTTPレスポンス # 非同期呼び出しのため、レスポンスは呼び出し元で利用されない
    """

    logger.info(f"START {os.path.basename(__file__)}")
    logger.debug(f"event: {event}")

    room_id = event.get("room_id")
    if not room_id:
        logger.error("Error: room_id not provided")
        return {"statusCode": 400, "body": "room_id required"}

    logger.info(f"Starting game timeout for room: {room_id}")

    # 60秒待機
    logger.info(f"Sleeping for {GAME_TIMEOUT_SECONDS} seconds...")
    time.sleep(GAME_TIMEOUT_SECONDS)

    logger.info(f"Timeout reached for room: {room_id}, sending timeout messages")

    try:
        # ルームのレコードを取得
        room: dict = room_repository.get_room_with_consistent_read(room_id)

        # ルーム履歴が存在するかを確認
        game_history_record = game_history_repository.get_game_history(
            f"pvp_battle_{room_id}"
        )
        if game_history_record:
            # 既にゲーム履歴が存在する場合、タイムアウト処理をスキップ(キャンセル等で終了したゲーム)
            logger.info(
                f"Game history for room {room_id} already exists. Skipping timeout processing."
            )
            logger.debug(f"game_history_record: {game_history_record}")
            return {"statusCode": 200, "body": "Game history already exists"}

        # ルームに接続しているコネクションレコードを取得
        connections: list = connection_repository.get_connections_by_room_id(room_id)

        if not connections:
            logger.info(f"No connections found for room: {room_id}")
            return {"statusCode": 200, "body": "No connections in room"}

        logger.debug("------connections------")
        logger.debug(f"Found {len(connections)} connections in room {room_id}")
        logger.debug(f"connections: {room}")
        logger.debug("-----------------")

        logger.debug("------room------")
        logger.debug(f"room: {room}")
        logger.debug("-----------------")

        # タイムアウトメッセージを作成
        timeout_message = {
            "type": "game_timeout",
            "data": {
                "message": "サーバー側でタイムアウトしました",
                "room_id": room_id,
                "player1_name": room.get("player1_name", "player1"),
                "player2_name": room.get("player2_name", "player2"),
                "player1_score": int(room.get("player1_score", 0)),
                "player2_score": int(room.get("player2_score", 0)),
            },
        }

        post_data = json.dumps(timeout_message)
        logger.info(f"Sending timeout message: {post_data}")

        # 全ての接続にタイムアウトメッセージを送信
        tasks = [
            async_send_message(post_data, connection) for connection in connections
        ]
        asyncio.run(async_main(tasks))

        logger.info(f"Timeout messages sent to all connections in room {room_id}")

        # ゲーム履歴を保存
        logger.info(f"Saving game history for room {room_id}")
        game_history_record = {
            "id": f"pvp_battle_{room_id}",
            "game_type": "pvp",  # プレイヤー対プレイヤーの対戦(他に"cpu"対戦がある)
            "room_id": room_id,
            "player1_name": room.get("player1_name", ""),
            "player2_name": room.get("player2_name", ""),
            "player1_score": int(room.get("player1_score", 0)),
            "player2_score": int(room.get("player2_score", 0)),
            "winner": get_winner(
                int(room.get("player1_score", 0)),
                int(room.get("player2_score", 0)),
                room.get("player1_name"),
                room.get("player2_name"),
            ),
            "end_reason": "normal_finish",
            "end_time": datetime.now(timezone.utc).isoformat(),
            "timestamp": int(time.time()),  # TTL用のunixタイムスタンプ
        }

        logger.debug(f"game_history_record: {game_history_record}")
        game_history_repository.create_game_history(game_history_record)

        logger.info(f"Game history saved for room {room_id}")

    except Exception as e:
        logger.error(f"Error sending timeout messages: {e}")
        return {"statusCode": 500, "body": f"Error: {str(e)}"}

    logger.info(f"END {os.path.basename(__file__)}")

    return {
        "statusCode": 200,
        "body": "Game timeout processed successfully",
    }
