import boto3


class ConnectionRepository:
    """Connectionテーブルへのアクセスを提供するリポジトリクラス
    """

    def __init__(self):
        """コンストラクタ
        テーブルアクセス用のオブジェクトを生成して保持する
        """
        dynamodb = boto3.resource("dynamodb")
        self.table = dynamodb.Table("Connection")

    def create_connection(self, connection_record):
        """コネクションレコードをConnectionテーブルに保存する

        Args:
            connection_record (dict): コネクションレコード
        """
        self.table.put_item(Item=connection_record)

    def get_connections_by_room_id(self, room_id):
        """指定されたルームIDに基づいて、接続中のコネクションレコードを取得する

        Args:
            room_id (str): ルームID ゲームを指定するキー

        Returns:
            list: コネクションレコードのリスト
        """
        response = self.table.query(
            IndexName="roomId-index",
            KeyConditionExpression=boto3.dynamodb.conditions.Key("room_id").eq(room_id)
        )
        return response.get("Items", [])

    def get_connection_by_id(self, connection_id):
        """指定されたコネクションIDに基づいて、コネクションレコードを取得する

        Args:
            connection_id (str): コネクションID WebSocket接続を指定するキー

        Returns:
            dict: コネクションレコード
        """
        response = self.table.get_item(Key={"id": connection_id})
        return response.get("Item", {})

    def get_room_id(self, connection_id):
        """指定されたコネクションIDに基づいて、ルームIDを取得する

        Args:
            connection_id (str): コネクションID WebSocket接続を指定するキー

        Returns:
            str: ルームID ゲームを指定するキー
        """
        connection = self.get_connection_by_id(connection_id)
        return connection.get("room_id")

    def delete_connection(self, connection_id):
        """指定されたコネクションIDに基づいて、コネクションレコードを削除する

        Args:
            connection_id (str): コネクションID WebSocket接続を指定するキー
        """
        self.table.delete_item(Key={"id": connection_id})
