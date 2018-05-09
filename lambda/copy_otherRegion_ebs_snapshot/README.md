## EC2スナップショットを異なるリージョンに複製

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

## 定期実行の設定

* Event sourcesとして`CloudWatch Events - Schedule`を選び以下のように設定する。
    * Rule name `copy_otherRegion_ebs_snapshot`
    * Rule description `19:00 UTC is 04:00 JST`
    * Schedule expression `cron(0 19 * * ? *)` （ https://docs.aws.amazon.com/ja_jp/AmazonCloudWatch/latest/DeveloperGuide/ScheduledEvents.html ）
        * 通常のcronと異なり最後に「年」の項目があるので注意。
    * Enable event source
        * Lambdaの定期実行の正体はCloudWatch Scheduleなので注意。一回設定した後の変更はCloudWatchでやる。
