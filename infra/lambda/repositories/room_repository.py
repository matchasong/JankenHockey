import boto3


class RoomRepository:
    """Roomテーブルへのアクセスを提供するリポジトリクラス
    """

    def __init__(self):
        """コンストラクタ
        テーブルアクセス用のオブジェクトを生成して保持する
        """
        dynamodb = boto3.resource("dynamodb")
        self.table = dynamodb.Table("Room")

    def create_room(self, room_record):
        """ルームレコードをRoomテーブルに保存する

        Args:
            room_record (dict): ルームレコード
        """
        self.table.put_item(Item=room_record)

    def get_room(self, room_id):
        """指定されたルームIDに基づいて、ゲームテーブルのレコードを取得する

        Args:
            room_id (str): ルームID ゲームを指定するキー

        Returns:
            dict: ゲームテーブルの1レコード
        """
        response = self.table.get_item(Key={"id": room_id})
        item = response.get("Item", {})
        print(f"get_room_record: {item}")
        return item

    def get_accessible_rooms(self):
        """アクセス可能なルームのリストを取得する

        Returns:
            list: アクセス可能なルームのリスト
        """
        response = self.table.scan(
            FilterExpression="joined = :joined_val AND (attribute_not_exists(accessible) OR accessible = :accessible_val)",
            ExpressionAttributeValues={
                ":joined_val": False,
                ":accessible_val": True
            }
        )
        rooms = response.get('Items', [])
        return rooms

    def get_cretor_name(self, room_id):
        """指定されたルームIDに基づいて、ルーム作成者の名前を取得する

        Args:
            room_id (str): ルームID ゲームを指定するキー

        Returns:
            str: ルーム作成者の名前
        """
        response = self.table.get_item(Key={"id": room_id})
        item = response.get("Item", {})
        return item.get("player1_name", "")

    def get_joiner_name(self, room_id):
        """指定されたルームIDに基づいて、ルーム参加者の名前を取得する

        Args:
            room_id (str): ルームID ゲームを指定するキー

        Returns:
            str: ルーム参加者の名前
        """
        response = self.table.get_item(Key={"id": room_id})
        item = response.get("Item", {})
        return item.get("player2_name", "")

    def get_room_with_consistent_read(self, room_id):
        """指定されたルームIDに基づいて、強い整合性読み込みでゲームテーブルのレコードを取得する

        Args:
            room_id (str): ルームID ゲームを指定するキー

        Returns:
            dict: ゲームテーブルの1レコード
        """
        response = self.table.get_item(Key={"id": room_id}, ConsistentRead=True)
        item = response.get("Item", {})
        print(f"get_room_record_with_consistent_read: {item}")
        return item

    def increment_score(self, room_id, player_name, player_class):
        """指定されたルームIDとプレイヤー名に基づいて、得点を1点加算する

        Args:
            room_id (str): ルームID ゲームを指定するキー
            player_name (str): プレイヤー名 プレイヤーの名前
            player_class (str): プレイヤークラス ("room_creator" または "room_joiner")
        """
        update_expression = ""
        expression_attribute_values = {}

        if player_class == "room_creator":
            update_expression = "SET player1_score = if_not_exists(player1_score, :start) + :inc"
            expression_attribute_values = {":inc": 1, ":start": 0}
        elif player_class == "room_joiner":
            update_expression = "SET player2_score = if_not_exists(player2_score, :start) + :inc"
            expression_attribute_values = {":inc": 1, ":start": 0}
        else:
            raise ValueError("Invalid player class. Must be 'room_creator' or 'room_joiner'.",
                             f"Got: {player_class}(player_name={player_name})")

        self.table.update_item(
            Key={"id": room_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_attribute_values
        )

    def update_creator_connection_id(self, room_id, connection_id):
        """指定されたルームIDに基づいて、ルーム作成者の接続IDを更新する

        Args:
            room_id (str): ルームID ゲームを指定するキー
            connection_id (str): 接続ID WebSocket接続を指定するキー
        """
        self.table.update_item(
            Key={"id": room_id},
            UpdateExpression="SET creatorConnectionId = :connection_id",
            ExpressionAttributeValues={":connection_id": connection_id}
        )

    def update_accessibility(self, room_id: str, accessible: bool):
        """
        単一アイテム（room）のアクセス可能状態を更新する。
        """
        self.table.update_item(
            Key={"id": room_id},
            UpdateExpression="SET accessible = :accessible",
            ExpressionAttributeValues={
                ":accessible": accessible
            }
        )

    def join_room_conditional(self, room_id: str, player_name: str):
        """
        単一アイテム（room）の条件付き更新で参加を確定する。
        - 条件: joined が未設定または false、かつ accessible = true
        """
        try:
            response = self.table.update_item(
                Key={"id": room_id},
                UpdateExpression="SET joined = :true, player2_name = :name",
                ConditionExpression="(attribute_not_exists(joined) OR joined = :false) AND accessible = :true",
                ExpressionAttributeValues={
                    ":true": True,
                    ":false": False,
                    ":name": player_name
                },
                ReturnValues="ALL_NEW"
            )
            return response.get("Attributes", {})
        except Exception as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                # 競合・条件不成立
                print(f"Join room conditional check failed for room_id={room_id}, player_name={player_name}")
                return None
            raise e
