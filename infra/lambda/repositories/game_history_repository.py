import boto3


class GameHistoryRepository:
    """GameHistoryテーブルへのアクセスを提供するリポジトリクラス"""

    def __init__(self):
        """コンストラクタ
        テーブルアクセス用のオブジェクトを生成して保持する
        """
        dynamodb = boto3.resource("dynamodb")
        self.table = dynamodb.Table("GameHistory")

    def create_game_history(self, game_history_record):
        """ゲーム履歴レコードをGameHistoryテーブルに保存する

        Args:
            game_history_record (dict): ゲーム履歴レコード
        """
        self.table.put_item(Item=game_history_record)

    def get_game_history(self, game_history_id):
        """指定されたIDに紐づくゲーム履歴レコードを取得する

        Args:
            game_history_id (str): ゲーム履歴ID

        Returns:
            list: ゲーム履歴レコード
        """
        response = self.table.get_item(Key={"id": game_history_id})
        return response.get("Item", [])
