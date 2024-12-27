import asyncio
import json
import os
import time

# from aws_requests_auth.aws_auth import AWSRequestsAuth
import aiohttp
import boto3

CONNECTION_TABLE_NAME = "Connection"
REGION = "ap-northeast-1"

# Dynamodbに接続
dynamodb = boto3.resource("dynamodb")
connection_table = dynamodb.Table(CONNECTION_TABLE_NAME)

# API Gateway Management APIに接続
api_endpoint = os.environ.get('API_ENDPOINT')
stage = os.environ.get('STAGE')

# AWSの認証情報を取得
boto3_session = boto3.Session()
credentials = boto3_session.get_credentials()
aws_access_key = credentials.access_key
aws_secret_access_key = credentials.secret_key
endpoint_host = api_endpoint.replace('wss://', '')
print(f"url_base: {endpoint_host}")

# API Gateway Management APIのエンドポイントを生成
# url = F"{api_endpoint}/{stage}".replace('wss', 'https')
# apigw_management = boto3.client('apigatewaymanagementapi', endpoint_url=F"{url}")


async def process_async_http_request(connection_id, data):
    """
    process_async_http_request
    非同期でHTTPリクエストを送信
    """
    start_async = time.perf_counter()
    print(f"connection_id: {connection_id}, data: {data}")

    # リクエスト署名の準備
    # auth = AWSRequestsAuth(
    #     aws_access_key=credentials.access_key,
    #     aws_secret_access_key=credentials.secret_key,
    #     aws_host=endpoint_host,
    #     aws_region=REGION,
    #     aws_service='execute-api'
    # )

    auth = aiohttp.helpers.BasicAuth("", "")

    post_url = f"https://{endpoint_host}/@connections/{connection_id}"
    print(f"post_url: {post_url}")

    async with aiohttp.ClientSession(auth=auth) as session:
        async with session.post(post_url, json=data) as response:
            print(f"response: {response.status}")
            print(f"response: {await response.text()}")

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
