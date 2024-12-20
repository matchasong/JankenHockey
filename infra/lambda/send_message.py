import asyncio
import json
import os
import time
import traceback

import aioboto3
import boto3

CONNECTION_TABLE_NAME = "Connection"
DELAY_TIME = 60

# Dynamodbに接続
dynamodb = boto3.resource("dynamodb")
connection_table = dynamodb.Table(CONNECTION_TABLE_NAME)

# API Gateway Management APIに接続
api_endpoint = os.environ.get('API_ENDPOINT')
stage = os.environ.get('STAGE')
url = F"{api_endpoint}/{stage}".replace('wss', 'https')
apigw_management = boto3.client('apigatewaymanagementapi', endpoint_url=F"{url}")

session = aioboto3.Session()
aio_client = session.client('apigatewaymanagementapi', endpoint_url=url)


async def async_send_message(post_data, item):
    """
    async_send_message
    """
    print("START async_send_message")
    await aio_client.post_to_connection(
        ConnectionId=item['id'],
        Data=post_data
    )
    print("END async_send_message")


async def async_main(post_data, items):
    """
    async_main
    """
    print("START async_main")
    tasks = [async_send_message(post_data, item) for item in items]
    try:
        # 現在のイベントループを取得
        loop = asyncio.get_event_loop()
        print("get_event_loop")
    except RuntimeError:
        # イベントループがない場合は新規作成
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        print("new_event_loop")

    await asyncio.gather(*tasks, return_exceptions=True)
    print("END async_main")


def handler(event, context):
    """
    handler
    """
    start_time = time.perf_counter()
    print(f"START {os.path.basename(__file__)}")
    print(f"stage: {stage}, api_endpoint: {api_endpoint}, {url}")
    print(f"event: {event}")

    post_data = json.loads(event.get('body', '{}')).get('data')
    print(f"post_data: {post_data} time: {time.perf_counter() - start_time}")

    items = connection_table.scan(ProjectionExpression='id').get('Items')
    if items is None:
        return {'statusCode': 500, 'body': 'no connection'}

    print(f"items:{items} time: {time.perf_counter() - start_time}")

    try:
        asyncio.run(async_main(post_data, items), debug=True)
    except TypeError:
        # 例外のスタックトレースを出力する
        traceback.print_exc()

    # 別スレッドの処理が終わる前にLambda環境がクローズしてしまうとまずいので、遅延を入れる
    time.sleep(DELAY_TIME)

    print(f"END {os.path.basename(__file__)} time: {time.perf_counter() - start_time}")
    return {
        "statusCode": 200,
        "body": "send message ok",
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "OPTIONS,POST,GET"
        }
    }
