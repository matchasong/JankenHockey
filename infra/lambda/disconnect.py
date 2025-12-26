from datetime import datetime, timezone
import json
import logging
import os
import time

import boto3

from repositories import RoomRepository, ConnectionRepository, GameHistoryRepository

# Dynamodbに接続
room_repository = RoomRepository()
connection_repository = ConnectionRepository()
game_history_repository = GameHistoryRepository()

# lambdaクライアント
lambda_client = boto3.client("lambda")
default_lambda_name = os.environ.get("DEFAULT_LAMBDA_NAME")

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
    Lambda関数(JankenHockeyDisconnectFunction)のhandler
    切断時にAPI Gateway経由で呼び出される。
    LambdaオーソライザーよりクライアントのconnectionIdを取得し、接続情報をConnectionテーブルから削除する。

    Args:
        event (dict): lambdaイベント
        context (dict): lambdaコンテキスト

    Returns:
        dict: HTTPレスポンス(CORSヘッダを含む)
    """

    logger.info(f"START {os.path.basename(__file__)}")
    logger.debug(f"event: {event}")

    # Get connection info before deleting to check if user was a room creator
    connection_id = event.get("requestContext", {}).get("connectionId")
    logger.debug(f"connection_id: {connection_id}")

    try:
        connection_item = connection_repository.get_connection_by_id(connection_id)

        if connection_item:
            room_id = connection_item.get("room_id")
            is_room_creator = connection_item.get("is_room_creator", False)
            player_name = connection_item.get("player_name")

            logger.info(
                f"Disconnecting user: {player_name}, room: {room_id}, creator: {is_room_creator}"
            )

            # If user was a room creator, mark their room as inaccessible
            if is_room_creator and room_id:
                room_repository.update_accessibility(room_id, accessible=False)
                logger.info(
                    f"Marked room {room_id} as inaccessible due to creator disconnect"
                )
            else:
                logger.info(f"Room {room_id} no longer exists, skipping update")
        else:
            logger.info(f"No connection info found for connection_id: {connection_id}")

    except Exception as e:
        logger.error(f"Error getting connection info: {e}")

    # 自分自身のユーザー名を取得
    connection_item = connection_repository.get_connection_by_id(connection_id)
    player_name_myself = connection_item.get("player_name")

    # 切断処理
    connection_repository.delete_connection(connection_id)
    logger.info(f"Deleted connection {connection_id} from Connection table")

    # ゲーム履歴の登録済みチェック(キャンセル済みまたは終了済みゲームは、キャンセルイベント送信をスキップ)
    existing_history = game_history_repository.get_game_history(f"pvp_battle_{room_id}")
    if existing_history:
        # ゲーム履歴に登録済み=キャンセル済みまたは終了済みゲームの場合、ここで処理を終了
        logger.info(f"Game history for room {room_id} already exists. Skipping save.")
        return {"statusCode": 200, "body": "Game history already exists"}

    # ゲーム履歴を登録
    # ルームのレコードを取得
    room: dict = room_repository.get_room_with_consistent_read(room_id)
    player1_name = room.get("player1_name")
    player2_name = room.get("player2_name")

    # 相手のユーザー名を取得
    another_player_name = ""
    if player_name_myself == player1_name:
        another_player_name = player2_name
    else:
        another_player_name = player1_name

    # ゲーム履歴レコードの作成
    if player1_name is None or player2_name is None:
        # ゲームが開始されていない場合(マッチングタイムアウト、または、マッチング前にルーム作成者がキャンセル)
        logger.info(
            f"Game is not started yet in room {room_id}. end reason set to 'no_start'."
        )
        game_history_record = {
            "id": f"pvp_battle_{room_id}",
            "game_type": "pvp",  # プレイヤー対プレイヤーの対戦(他に"cpu"対戦がある)
            "room_id": room_id,
            "player1_name": player1_name,
            "player2_name": player2_name,
            "player1_score": int(room.get("player1_score", 0)),
            "player2_score": int(room.get("player2_score", 0)),
            "end_reason": "no_start",
            "winner": "",
            "end_time": datetime.now(timezone.utc).isoformat(),
            "timestamp": int(time.time()),  # TTL用のunixタイムスタンプ
        }

    else:
        # ゲームが開始されている場合
        logger.info(
            f"Game is in progress in room {room_id}. end reason set to 'disconnect'."
        )
        game_history_record = {
            "id": f"pvp_battle_{room_id}",
            "game_type": "pvp",  # プレイヤー対プレイヤーの対戦(他に"cpu"対戦がある)
            "room_id": room_id,
            "player1_name": player1_name,
            "player2_name": player2_name,
            "player1_score": int(room.get("player1_score", 0)),
            "player2_score": int(room.get("player2_score", 0)),
            "end_reason": "disconnect",
            "winner": another_player_name,
            "end_time": datetime.now(timezone.utc).isoformat(),
            "timestamp": int(time.time()),  # TTL用のunixタイムスタンプ
        }

    logger.debug(f"game_history_record: {game_history_record}")
    game_history_repository.create_game_history(game_history_record)
    logger.info(f"Game history saved for room {room_id}")

    # キャンセルも終了もしていないゲームの場合
    # cancelイベントをWebSocketに送信
    if player1_name is None or player2_name is None:
        logger.info("Sending cancel event.")
        payload = {
            "data": {"type": "cancel", "player": player_name},
        }

        logger.info("Invoking send_message lambda")
        logger.debug(f"payload: {payload}")

        lambda_client.invoke(
            FunctionName=default_lambda_name,
            InvocationType="Event",
            Payload=json.dumps(payload),
        )
        logger.info("Cancel event sended.")

    logger.info(f"END {os.path.basename(__file__)}")

    return {
        "statusCode": 200,
        "body": "disconnect ok",
    }
