import os
import logging
import boto3

from repositories import RoomRepository, ConnectionRepository

# Dynamodbに接続
room_repository = RoomRepository()
connection_repository = ConnectionRepository()

# lambdaクライアント
lambda_client = boto3.client("lambda")
send_message_lambda_name = os.environ.get(
    "SEND_MESSAGE_LAMBDA_NAME", "JankenHockeySendMessageFunction"
)

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
    Lambda関数(JankenHockeyConnectFunction)のhandler
    ゲーム開始時にAPI Gateway経由で呼び出される。
    Lambdaオーソライザーよりクライアントのユーザー名と選択したルームIDを取得し、接続情報をConnectionテーブルに登録する。

    Args:
        event (dict): lambdaイベント
        context (dict): lambdaコンテキスト

    Returns:
        dict: HTTPレスポンス(CORSヘッダを含む)
    """

    logger.info(f"START {os.path.basename(__file__)}")
    logger.debug(f"event: {event}")

    # Originヘッダの確認(WebSocketではCORSヘッダによる制御はできないため、明示的にチェック)
    request_origin = event.get("headers", {}).get("Origin")
    expected_origin = os.environ.get("CLOUDFRONT_ORIGIN_URL")
    logger.debug(
        f"Request origin: {request_origin}, Expected origin: {expected_origin}"
    )

    if request_origin != expected_origin:
        logger.warning(f"Invalid origin {request_origin}. Rejecting connection.")
        return {
            "statusCode": 403,
            "body": "Forbidden",
        }

    # Get username from authorizer context (authenticated user)
    authorizer_context = event.get("requestContext", {}).get("authorizer", {})
    username = authorizer_context.get("username", "unknown")

    # Get other parameters from query string
    query_string_parameters = event.get("queryStringParameters", {})
    room_id = query_string_parameters.get("roomId", None)
    is_room_creator = query_string_parameters.get("isRoomCreator").lower() == "true"

    connection_id = event.get("requestContext", {}).get("connectionId")
    logger.debug(
        f"connection_id: {connection_id} username: {username} room_id: {room_id} is_room_creator: {is_room_creator}"
    )

    # Connectionテーブルに登録
    connection_record = {
        "id": connection_id,
        "room_id": room_id,
        "player_name": username,  # Use authenticated username instead of query parameter
        "is_room_creator": is_room_creator,
    }

    logger.info(f"Creating connection record: {connection_record}")
    connection_repository.create_connection(connection_record=connection_record)
    logger.info(f"Insert to Connection Table: Result: {connection_record}")

    # ルーム作成者の場合、RoomテーブルのcreatorConnectionIdを更新
    if is_room_creator and room_id:
        logger.info(
            f"Room creator connected, updating Room Table's creatorConnectionId. room_id:{room_id}"
        )
        try:
            room_repository.update_creator_connection_id(
                room_id=room_id, connection_id=connection_id
            )
            logger.info(
                f"Updated Room {room_id} creatorConnectionId to {connection_id}"
            )
        except Exception as e:
            logger.error(f"Error updating Room creatorConnectionId: {e}")

    logger.info(f"END {os.path.basename(__file__)}")

    return {"statusCode": 200, "body": "connect ok"}
