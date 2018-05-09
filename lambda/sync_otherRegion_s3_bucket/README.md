# 特定環境S3の一部バケットを異なるリージョンに同期する

bucket01.exsample.com
bucket02.exsample.com
bucket03.exsample.com
「dr-<上記ホスト名>」のバケットに同期  

## AWS Lambda実行環境へのAWS CLIの実装

* [参考文献] https://alestic.com/2016/11/aws-lambda-awscli/
    * 当該サイトが無くなったときに備えて末尾「AWS CLI導入手順（転記）」として概要を転記。
* 「lambda.zip」にインポートする「XXX.py」は事前に作成しておく
* 「XXX.py」にAWS CLIコマンドを実装する際の注意点
    * 「import command」は使用できない為「import subprocess」を用いる
    *  subprocess.call(<command>, stderr=subprocess.STDOUT)など
    *  尚、shell=Trueでシェルを明示的に呼びだした場合、シェルインジェクションの脆弱性対策を施す事
* apexにて配備後、AWS コンソールのLambdaで対象の関数設定を開く。「コードエントリタイプ」からZIPファイルを選択し、アップロード後保存する。

## 定期実行の設定

* Event sourcesとして`CloudWatch Events - Schedule`を選び以下のように設定する。
    * Rule name `sync_otherRegion_s3_bucket`
    * Rule description `every hh:25`
    * Schedule expression `cron(25 * * * ? *)` （ https://docs.aws.amazon.com/ja_jp/AmazonCloudWatch/latest/DeveloperGuide/ScheduledEvents.html ）
        * 通常のcronと異なり最後に「年」の項目があるので注意。
    * Enable event source
        * Lambdaの定期実行の正体はCloudWatch Scheduleなので注意。一回設定した後の変更はCloudWatchでやる。

## 配備手順（apex）

* 当ソースをローカルにcloneする。
* 当ソースを変更する。
* 当ソースの変更をcommit/pushする。
* 開発環境は `apex deploy --profile <プロファイル名> --env <prd> or <stg> or <dev>` を実行する
* ※事前に `~/.aws` 内にプロファイルを作成してあること
* ※関数名ディレクトリ直下に移動、ここでは「copy_otherRegion_ebs_snapshot」

* [パーミッション]
    * .aws [775]
    * - config [600]
    * - credentials [600]

## AWS CLI導入手順（転記）

Here are the steps I followed to add aws-cli to my AWS Lambda function. Adjust to suit your particular preferred way of building AWS Lambda functions.

Create a temporary directory to work in, including paths for a temporary virtualenv, and an output ZIP file:

```
tmpdir=$(mktemp -d /tmp/lambda-XXXXXX)
virtualenv=$tmpdir/virtual-env
zipfile=$tmpdir/lambda.zip
```

Create the virtualenv and install the aws-cli Python package into it using a subshell:

```
(
  virtualenv $virtualenv
  source $virtualenv/bin/activate
  pip install awscli
)
```

Copy the aws command file into the ZIP file, but adjust the first (shabang) line so that it will run with the system python command in the AWS Lambda environment, instead of assuming python is in the virtualenv on our local system. This is the valuable nugget of information buried deep in this article!

```
rsync -va $virtualenv/bin/aws $tmpdir/aws
perl -pi -e '$_ = "#!/usr/bin/python\n" if $. == 1' $tmpdir/aws
(cd $tmpdir; zip -r9 $zipfile aws)
```

Copy the Python packages required for aws-cli into the ZIP file:

```
(cd $virtualenv/lib/python2.7/site-packages; zip -r9 $zipfile .)
```

Copy in your AWS Lambda function, other packages, configuration, and other files needed by the function code. These don’t need to be in Python.

```
cd YOURLAMBDADIR
zip -r9 $zipfile YOURFILES
```

Upload the ZIP file to S3 (or directly to AWS Lambda) and clean up:

```
aws s3 cp $zipfile s3://YOURBUCKET/YOURKEY.zip
rm -r $tmpdir
```

In your Lambda function, you can invoke aws-cli commands. For example, in Python, you might use:

```
import subprocess
command = ["./aws", "s3", "sync", "--acl", "public-read", "--delete",
           source_dir + "/", "s3://" + to_bucket + "/"]
print(subprocess.check_output(command, stderr=subprocess.STDOUT))
```

Note that you will need to specify the location of the aws command with a leading "./" or you could add /var/task (cwd) to the $PATH environment variable.
