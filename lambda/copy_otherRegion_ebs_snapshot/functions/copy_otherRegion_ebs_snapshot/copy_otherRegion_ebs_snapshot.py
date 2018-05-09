# coding:utf-8
# From : Asia Pacific (Tokyo) ap-northeast-1
# To : US East (N. Virginia) us-east-1
import boto3
import collections
import time
from datetime import datetime,timedelta
from botocore.exceptions import ClientError

SRC_REGION = 'ap-northeast-1'
DEST_REGION = 'us-east-1'
STORED_SNAPTHOT_NUM = 2

def lambda_handler(event, context):
    _copy_snapshots()
    _del_snapshots()
    print("[Copy Snapshot Complete] " + datetime.now().strftime("%Y/%m/%d %H:%M:%S"))


## 転送元スナップショット取得
def get_snapshots_descriptions_src():

    ec2 = boto3.client('ec2', region_name=SRC_REGION)
    snapshots = ec2.describe_snapshots(
        Filters=[
            {
                'Name':'State',
                'Values':['completed'],
                'Name':'tag-key',
                'Values':['IsAutoBackup'],
                'Name':'tag-value',
                'Values':['1'],
            }
        ]
    )['Snapshots']

    groups = {}
    groups = collections.defaultdict(lambda: [])
    { groups[ s['Description'] ].append(s) for s in snapshots }

    return groups


## スナップショットコピー処理
def _copy_snapshots():

    print("[Copy Snapshot Processing] " + datetime.now().strftime("%Y/%m/%d %H:%M:%S"))

    copyList = []
    srcSnapshots = get_snapshots_descriptions_src()
    for description, snapshots in srcSnapshots.items():

        try:

            SnapshotId = snapshots[0]['SnapshotId']

            # コピー
            ec2 = boto3.client('ec2', region_name=DEST_REGION)
            res = ec2.copy_snapshot(
                Description = description,
                DestinationRegion = DEST_REGION,
                SourceRegion = SRC_REGION,
                SourceSnapshotId = SnapshotId,
            )
            copyList.append(res)

            # タグ付け
            print("[Tagging] " + datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
            print(description + "：" + SnapshotId)
            for r in copyList:

                ec2.create_tags(
                    Resources=[
                        r['SnapshotId'],
                    ],
                    Tags=[
                        {'Key': 'IsAvailableBackup', 'Value': '1'}
                    ]
                )

        except ClientError as e:
            print "ERROR: %s" % e


## 転送先スナップショット取得
def get_snapshots_descriptions_dist():

    ec2 = boto3.client('ec2', region_name=DEST_REGION)
    snapshots = ec2.describe_snapshots(
        Filters=[
            {
            'Name':'tag-key',
            'Values':['IsAvailableBackup'],
            'Name':'tag-value',
            'Values':['1'],
            }
        ]
    )['Snapshots']

    groups = {}
    snapshots = sorted(snapshots, key=lambda x: int(x['StartTime'].strftime('%s')), reverse=True)
    groups = collections.defaultdict(lambda: [])
    { groups[ s['Description'] ].append(s) for s in snapshots }

    _check_snapshots(groups)
    return groups


## 転送先スナップショット削除
def _del_snapshots():

    print("[Delete Snapshot Processing] " + datetime.now().strftime("%Y/%m/%d %H:%M:%S"))

    # スナップショット取得
    distSnapshots = get_snapshots_descriptions_dist()

    # 旧スナップショット削除
    ec2 = boto3.client('ec2', region_name=DEST_REGION)
    for description, snapshots in distSnapshots.items():
        if len(snapshots) < (STORED_SNAPTHOT_NUM + 1):
            print "WARN: There is no enough stored snapshots of %s" % (description)
        delSnapshots = snapshots[STORED_SNAPTHOT_NUM:]
        for s in delSnapshots:
            try:
                ec2.delete_snapshot(SnapshotId=s['SnapshotId'])
                print "[Delete Snapshot] %s(%s %s)" % (s['SnapshotId'], s['Description'], s['StartTime'])
            except ClientError as e:
                print "ERROR: %s" % e


## 転送先スナップショット確認
def _check_snapshots(snapshotList):

        for description, snapshots in snapshotList.items():

            StartTime = snapshots[0]['StartTime'] + timedelta(hours=9)
            time1 = datetime.strftime(StartTime,'%Y-%m-%d %H:%M:%S,%f')
            time2 = datetime.now().strftime('%Y-%m-%d %H:%M:%S,%f')
            tap_t1 = time.strptime(time1,'%Y-%m-%d %H:%M:%S,%f')
            tap_t2 = time.strptime(time2,'%Y-%m-%d %H:%M:%S,%f')
            epo_time_t1 = time.mktime(tap_t1)
            epo_time_t2 = time.mktime(tap_t2)
            diffTime = epo_time_t2 - epo_time_t1

            # 2日以上の差がある場合警告
            if 172800 < diffTime:
                print "WARN: Snapshot hasn't been acquired for more than 2 day %s" % (description)
