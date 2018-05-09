# coding:utf-8
# From : Asia Pacific (Tokyo) ap-northeast-1
# To : US East (N. Virginia) us-east-1
import boto3
import botocore
import os
from datetime import datetime
from subprocess import Popen, PIPE
s3 = boto3.resource('s3')
sts = boto3.client('sts')

## 環境情報取得
id_info = sts.get_caller_identity()
accountID = id_info['Account']

## 同期バケット設定
syncBucketList = {

    # 開発
    "000000000000":
        [
            ['dev-bucket.exsample.com-from', 'dev-bucket.exsample.com-to', []],
        ],

    # 本番
    "000000000000":
        [
            ['bucket01.exsample.com', 'dr-bucket01.exsample.com', []],
            ['bucket02.exsample.com', 'dr-bucket02.exsample.com', []],
            ['bucket03.exsample.com', 'dr-bucket03.exsample.com', ['--exclude', '"*.png"']],
        ]

}

## SyncBuckets
def lambda_handler(event, context):

    # 環境変数
    localenv = os.environ.copy()
    localenv["AWS_CONFIG_FILE"] = "./sync_otherRegion_s3_bucket_config.txt"

    for r in syncBucketList[accountID]:

        srcBucket = r[0]
        distBucket = r[1]
        cmdOption = r[2]
        exists = True
        print("[Sync Processing] " + datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
        print(srcBucket + " > " + distBucket)

        try:

            # バケット確認
            s3.meta.client.head_bucket(Bucket=srcBucket)
            s3.meta.client.head_bucket(Bucket=distBucket)

            # 同期コマンド生成
            command = [
                "./aws", "s3", "sync",
                "s3://" + srcBucket + "/",
                "s3://" + distBucket + "/",
                "--exact-timestamps",
                "--delete"
            ]
            command.extend(cmdOption)

            # 同期処理
            print command
            proc = Popen(command, stdout=PIPE, stderr=PIPE, env=localenv)
            out, err = proc.communicate()
            print out
            print err
            print("[Sync Processing Complete] " + datetime.now().strftime("%Y/%m/%d %H:%M:%S"))

        except botocore.exceptions.ClientError as e:

            error_code = int(e.response['Error']['Code'])
            print("ERROR: " + datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
            print(e.response['Error'])
            if error_code == 404:
                exists = False
