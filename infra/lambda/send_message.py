import asyncio
import json
import os
import time

import aiohttp
import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.credentials import Credentials

# 定数
CONNECTION_TABLE_NAME = "Connection"
REGION = "ap-northeast-1"
METHOD_POST = "POST"

# 環境変数からcredentialsを取得
aws_access_key = os.environ.get('AWS_ACCESS_KEY_ID')
aws_secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
aws_session_token = os.environ.get('AWS_SESSION_TOKEN')
aws_region = os.environ.get('AWS_REGION')

# 実行ロールの情報を取得
sts_client = boto3.client('sts')
identity = sts_client.get_caller_identity()

# Dynamodbに接続
dynamodb = boto3.resource("dynamodb")
connection_table = dynamodb.Table(CONNECTION_TABLE_NAME)

# API Gateway Management APIに接続
api_endpoint = os.environ.get('API_ENDPOINT')
stage = os.environ.get('STAGE')

# API Gatewayのエンドポイントを取得
endpoint_host = api_endpoint.replace('wss://', '')
print(f"endpoint_host: {endpoint_host}")

# AWSの認証情報を取得
boto3_session = boto3.Session()
credentials: Credentials = boto3_session.get_credentials()

# SigV4の署名を作成
auth = SigV4Auth(credentials, "execute-api", f"{REGION}")

# aiohttp.ClientSessionの初期化
session = None


async def get_session() -> aiohttp.ClientSession:
    """get_session
    aiohttp.ClientSessionオブジェクトを返す
    すでに作成済みの場合は再作成しない

    Returns:
        aiohttp.ClientSession: aiohttp.ClientSessionオブジェクト
    """
    global session
    if session is None:
        session = aiohttp.ClientSession()
    return session


async def process_async_http_request(connection_id, data):
    """
    process_async_http_request
    非同期でHTTPリクエストを送信
    """
    start_async = time.perf_counter()
    print(f"connection_id: {connection_id}, data: {data}")

    url = f"https://{endpoint_host}/{stage}/@connections/{connection_id}"
    print(f"post_url: {url}")

    # AWSリクエストの作成
    aws_request = AWSRequest(
        method=METHOD_POST,
        url=url,
        data=data,
        headers={
            'Content-Type': 'application/json'
        }
    )

    # SigV4で署名
    auth.add_auth(aws_request)

    # async with aiohttp.ClientSession() as session:
    session = await get_session()
    async with session.post(
        url,
        headers=dict(aws_request.headers),
        data=data
    ) as response:
        print(f"response: {response.status}")
        print(f"Headers: {response.headers}")

    print(f"process_async_http_request time: {time.perf_counter() - start_async}")


async def async_send_message(post_data, item):
    """
    async_send_message
    """
    await process_async_http_request(item['id'], post_data)
    # await asyncio.to_thread(apigw_management.post_to_connection(ConnectionId=item['id'], Data=post_data))


async def async_main(tasks):
    """
    async_main
    """
    await asyncio.gather(*tasks)


def handler(event, context):
    """
    handler
    """
    start_time = time.perf_counter()
    print(f"START {os.path.basename(__file__)}")
    print(f"stage: {stage}, api_endpoint: {api_endpoint}")
    print(f"event: {event}")

    post_data = json.loads(event.get('body', '{}')).get('data')
    print(f"post_data: {post_data} time: {time.perf_counter() - start_time}")

    items = connection_table.scan(ProjectionExpression='id').get('Items')
    if items is None:
        return {'statusCode': 500, 'body': 'no connection'}

    print(f"items:{items} time: {time.perf_counter() - start_time}")

    tasks = [async_send_message(post_data, item) for item in items]
    asyncio.run(async_main(tasks), debug=True)

    print(f"async_main called time: {time.perf_counter() - start_time}")

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
