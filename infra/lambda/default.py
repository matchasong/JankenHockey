import asyncio
import json
import logging
import os
import time

from abc import ABC, abstractmethod
import boto3
from typing import Dict, List, Optional

from repositories import RoomRepository, ConnectionRepository


# Dynamodbに接続
room_repository = RoomRepository()
connection_repository = ConnectionRepository()

# lambdaクライアント
lambda_client = boto3.client("lambda")
game_timeout_lambda_name = os.environ.get(
    "GAME_TIMEOUT_LAMBDA_NAME", "JankenHockeyGameTimeoutFunction"
)

# API Gateway Management APIに接続
api_endpoint = os.environ.get("API_ENDPOINT")
stage = os.environ.get("STAGE")
url = f"{api_endpoint}/{stage}".replace("wss", "https")
apigw_management = boto3.client("apigatewaymanagementapi", endpoint_url=f"{url}")

# logger setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    force=True,
)
logger = logging.getLogger(__name__)


async def send_message(post_data, item):
    """
    async_send_message
    """
    try:
        await asyncio.to_thread(
            apigw_management.post_to_connection, ConnectionId=item["id"], Data=post_data
        )
        logger.info(f"Sent message to connection {item['id']}")
    except apigw_management.exceptions.GoneException:
        logger.error(
            f"GoneException: connection {item['id']} is gone. Deleting from DynamoDB."
        )
        connection_repository.delete_connection_by_id(item["id"])
    except Exception as e:
        logger.error(f"Exception sending message to {item['id']}: {e}")


async def send_websocket_messages(send_data, connections):
    """
    send_websocket_messages

    Args:
        send_data (dict): データ
        connections (list[dict]): WebSocket接続情報
    """
    # サーバーから各クライアントへの通信を発信
    send_data_json = json.dumps(send_data)
    logger.debug(send_data_json, connections)
    tasks = [send_message(send_data_json, connection) for connection in connections]
    await asyncio.gather(*tasks)


class EventStrategy(ABC):
    """イベント処理の基底クラス"""

    def __init__(self, room_id: str, connection_id: str, connections: List[Dict]):
        self.room_id = room_id
        self.connection_id = connection_id
        self.connections = connections
        self.connection_count = len(connections) if connections else 0

    @abstractmethod
    async def execute(self, data: dict):
        """
        イベント処理を実行

        Returns:
            ブロードキャストするメッセージ（Noneの場合はブロードキャストしない）
        """
        pass


class WaitEventStrategy(EventStrategy):
    """waitイベント: プレイヤー準備完了"""

    async def execute(self, data: Dict) -> Optional[Dict]:
        player_name = data.get("player")
        logger.info(f"Player {player_name} waiting in room {self.room_id}")

        if self.connection_count == 1:
            # 1人目: 待機中
            return {"type": "wait", "message": "Waiting for opponent"}

        elif self.connection_count == 2:
            # 2人揃った: ゲーム開始
            logger.info(f"Room {self.room_id}: Both players ready!")

            # タイムアウトLambdaを起動
            self._invoke_timeout_lambda()

            # startイベントを作成
            creator_name = room_repository.get_cretor_name(self.room_id)
            joiner_name = room_repository.get_joiner_name(self.room_id)

            start_data = {
                "type": "start",
                "data": {"creatorName": creator_name, "joinerName": joiner_name},
            }

            return start_data

        else:
            logger.error(
                f"Room {self.room_id}: Invalid connection count {self.connection_count}"
            )
            raise ValueError(f"Invalid connection count {self.connection_count}")

    def _invoke_timeout_lambda(self):
        """ゲームタイムアウトLambdaを起動"""
        try:
            lambda_client.invoke(
                FunctionName=game_timeout_lambda_name,
                InvocationType="Event",
                Payload=json.dumps({"room_id": self.room_id}),
            )
            logger.info(f"Timeout Lambda invoked for room {self.room_id}")
        except Exception as e:
            logger.error(f"Error invoking timeout Lambda: {e}")


class BallEventStrategy(EventStrategy):
    """ballイベント: ボール発射"""

    async def execute(self, data: Dict) -> Optional[Dict]:
        return {"type": "ball", "data": data}


class NextHandsEventStrategy(EventStrategy):
    """next_handsイベント: 次の手の情報"""

    async def execute(self, data: Dict) -> Optional[Dict]:
        return {"type": "next_hands", "data": data}


class LauncherPositionEventStrategy(EventStrategy):
    """launcher_positionイベント: 発射台の位置"""

    async def execute(self, data: Dict) -> Optional[Dict]:
        return {"type": "launcher_position", "data": data}


class PointEventStrategy(EventStrategy):
    """pointイベント: 得点"""

    async def execute(self, data: Dict) -> Optional[Dict]:
        player_name = data.get("player")
        self._update_score(player_name)
        return {"type": "point", "data": data}

    def _update_score(self, player_name: str):
        """得点を更新"""
        creator_name = room_repository.get_cretor_name(self.room_id)
        joiner_name = room_repository.get_joiner_name(self.room_id)

        if player_name == creator_name:
            room_repository.increment_score(self.room_id, player_name, "room_creator")
            logger.info(f"Score++ for creator {player_name}")
        elif player_name == joiner_name:
            room_repository.increment_score(self.room_id, player_name, "room_joiner")
            logger.info(f"Score++ for joiner {player_name}")
        else:
            error_msg = f"Unknown player {player_name} in room {self.room_id}"
            logger.error(error_msg)
            raise ValueError(error_msg)


class CancelEventStrategy(EventStrategy):
    """cancelイベント: ゲーム中止"""

    async def execute(self, data: Dict) -> Optional[Dict]:
        logger.info(f"Game cancelled by {data.get('player')}")
        return {"type": "cancel", "data": data}


class EndEventStrategy(EventStrategy):
    """endイベント: ゲーム終了"""

    async def execute(self, data: Dict) -> Optional[Dict]:
        logger.info(f"Game ended in room {self.room_id}")
        return {"type": "end", "data": data}


# ストラテジーファクトリー
class EventStrategyFactory:
    """イベントタイプに応じた適切なストラテジーを生成"""

    _strategies = {
        "wait": WaitEventStrategy,
        "ball": BallEventStrategy,
        "next_hands": NextHandsEventStrategy,
        "launcher_position": LauncherPositionEventStrategy,
        "point": PointEventStrategy,
        "cancel": CancelEventStrategy,
        "end": EndEventStrategy,
    }

    @classmethod
    def create(
        cls, event_type: str, room_id: str, connection_id: str, connections: List[Dict]
    ) -> EventStrategy:
        """ストラテジーを生成"""
        strategy_class = cls._strategies.get(event_type)
        if strategy_class:
            return strategy_class(room_id, connection_id, connections)
        else:
            raise ValueError(
                f"Unknown event type: '{event_type}'. "
                f"Supported types: {', '.join(cls._strategies.keys())}"
            )


def handler(event, context):
    """
    handler

    defaultパスに対応したLambda関数
    """
    start_time = time.perf_counter()
    logger.info("START handler")

    try:
        # 前処理
        # リクエストから情報を取得
        connection_id = event.get("requestContext", {}).get("connectionId")

        body = json.loads(event.get("body", "{}"))
        data = body.get("data", {})
        event_type = data.get("type")

        logger.info(f"Event: {event_type} from {connection_id}")

        # ルーム情報および接続情報を取得
        room_id = connection_repository.get_room_id(connection_id)
        connections = connection_repository.get_connections_by_room_id(room_id)

        logger.info(f"Room {room_id}: {len(connections)} connection(s)")

        # 主処理
        # ストラテジーを生成して実行
        strategy = EventStrategyFactory.create(
            event_type, room_id, connection_id, connections
        )
        response_message = asyncio.run(strategy.execute(data))

        # レスポンスをブロードキャスト
        if response_message:
            asyncio.run(send_websocket_messages(response_message, connections))

        logger.info(f"Successfully processed {event_type}")

        # 後処理
        elapsed = time.perf_counter() - start_time
        logger.info(f"END handler - Duration: {elapsed:.3f}s")

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Success"}),
        }

    except Exception as e:
        logger.error(f"Error in handler: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
        }
