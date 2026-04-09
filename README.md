# 匿名関数の置き換えに関する調査

## 環境

docker が最も簡単．以下のコマンドで環境を再現できる．

```sh
docker compose up --build -d
docker compose exec lambda bash
```

初回にコンテナ内で以下を実行する必要がある．

```sh
uv sync
```

個別だと以下に従う．

- Python
  - version 3.12
  - uv を使うのが便利．`uv sync`で環境を再現可能
  - あるいは requirements.txt からパッケージをインストール
- Java
  - OpenJDK 17
- srcML
  - [こちら](https://www.srcml.org/#download)からダウンロードして`srcml`を実行できるようにする

## データ

### ダウンロード

- [こちら](https://zenodo.org/records/3626071)から libraries-1.6.0-2020-01-12.tar.gz を data にダウンロードし，解凍する
- 以下のコマンドでも可

```sh
curl -LC - --retry 999 --retry-connrefused --retry-max-time 0 -o data/libraries-1.6.0-2020-01-12.tar.gz "https://zenodo.org/api/records/3626071/files/libraries-1.6.0-2020-01-12.tar.gz/content" -#
tar -zxvf data/libraries-1.6.0-2020-01-12.tar.gz
```

### データ前処理

```sh
uv run python  src/python/preprocessing.py
```

## 実行

### 1. Java をパッケージング

```sh
mvn clean package -f "src/java/pom.xml"
```

### 2. Replacement収集スクリプトを実行

- language は cpp・csharp・java・javascript・php・ruby のいずれか

```sh
uv run python src/python/collect_lambda.py -l <language>
```

あるいは，以下で実行．これは並列実行を行う

```sh
uv run python python/collect_lambda_ray.py -l <language> -n <num_cpus>
```

### 3. RQ3用のスクリプトを実行する

```sh
uv run python collect_delete_matching.py -l <language>
```

```sh
uv run python collect_delete_matching_ray.py -l <language> -n <num_cpus>
```

### 4. RQ4用のスクリプトを実行する

```sh
uv run python rq4_preprocessing.py
```

## オープンコーディング

RQ4のオープンコーディングについては

<https://github.com/posl/tomoto_lambda_open_coding>

にまとまっている

## 結果の確認

`notebooks/rq{n}.ipynb`が各RQの結果を出力するコードが，`/results/rq{n}`に各RQの結果が格納されている
