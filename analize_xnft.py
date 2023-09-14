import os
import requests
import psycopg2
from psycopg2 import extras
import pandas as pd
import json
import random
import math
from itertools import accumulate # Gini係数を計算する
import numpy as np


# URL取得
def get_api_urls(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT id,api_url FROM nft_products WHERE is_inactive = FALSE;")
    api_urls = [{"id": row[0], "url": row[1]} for row in cursor.fetchall()]
    cursor.close()
    return api_urls

# 外れ値を計算する関数
def compute_outliers(data):
    if not data:
        return []
    Q1 = np.percentile(data, 25)
    Q3 = np.percentile(data, 75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    outliers = [point for point in data if point < lower_bound or point > upper_bound]
    outliers = [int(value) for value in outliers]
    return outliers

# 層化ランダムサンプリング
def sampled_outliers(outliers):
    if not outliers:
        return []

    # データをソート
    sorted_outliers = sorted(outliers)

    # 最大値と最小値を取得
    min_value = sorted_outliers[0]
    max_value = sorted_outliers[-1]

    # 最大値と最小値を除いたデータ
    remaining_outliers = sorted_outliers[1:-1]

    # 3つの層に分割
    split_indices = len(remaining_outliers) // 3
    layer1 = remaining_outliers[:split_indices]
    layer2 = remaining_outliers[split_indices:2*split_indices]
    layer3 = remaining_outliers[2*split_indices:]

    # 各層からランダムにデータをサンプリング
    sampled_layer1 = random.choice(layer1)
    sampled_layer2 = random.choice(layer2)
    sampled_layer3 = random.choice(layer3)

    # サンプリング結果を結合
    stratified_sample = [min_value, sampled_layer1, sampled_layer2, sampled_layer3, max_value]
    return stratified_sample

# データセットの例を使用して箱ひげ図のパラメータを計算
def compute_boxplot_parameters(data):
    counts = [item['count'] for item in data]
    temp = np.array(counts)

    # 中央値 (Median)
    median = np.percentile(temp, 50)
    # 第1四分位数 (Q1)
    Q1 = np.percentile(temp, 25)
    # 第3四分位数 (Q3)
    Q3 = np.percentile(temp, 75)
    # 四分位範囲 (IQR)
    IQR = Q3 - Q1
    # 上ヒゲの終端
    upper_whisker = temp[temp <= Q3 + 1.5 * IQR].max()
    # 下ヒゲの終端
    lower_whisker = temp[temp >= Q1 - 1.5 * IQR].min()
    
    return {
        'q1': int(Q1),
        'q3': int(Q3),
        'iqr': int(IQR),
        'median': int(median),
        'outliers': sampled_outliers(compute_outliers(counts)),
        'lower_whisker': int(lower_whisker),
        'upper_whisker': int(upper_whisker)
    }

# オーナリスト
def get_top10_owner_list(data):
    df_owners = pd.DataFrame(data['owners']).sort_values(by='count', ascending=False)
    top10_owners_df = df_owners.head(10)[['owner', 'count']]
    data_dict = top10_owners_df.to_dict('records')
    return data_dict

# フェッチ
def fetch_data(url):
    # APIを実行
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error with status code: {response.status_code}")
        return None

# オーナー情報を取得
def get_owner_data(data):
    if len(data['owners']) <= 0:
        return None
    # owners から owner と count の情報を取得
    owners_list = [(item['owner'], item['count']) for item in data['owners']]
    # DataFrameに変換
    df = pd.DataFrame(owners_list, columns=['owners', 'count'])
    data_dict = df.to_dict('records')
    return data_dict

# オーナー情報を取得
def get_owner_data2(data):
    if len(data['owners']) <= 0:
        return None
    df_owners = pd.DataFrame(data['owners']).sort_values(by='count', ascending=False).reset_index(drop=True)
    owner_data = {}
    owner_data['top10_owners'] = get_top10_owner_list(data)
    owner_data['top10_owners_count'] = df_owners.head(10)['count'].sum()
    owner_data['other_owners_count'] = df_owners[10:]['count'].sum()
    owner_data['total_owners'] = len(df_owners)
    owner_data['owners_1_count'] = len(df_owners[df_owners['count'] == 1])
    owner_data['owners_2_3_count'] = len(df_owners[df_owners['count'].isin([2, 3])])
    owner_data['owners_4_10_count'] = len(df_owners[(df_owners['count'] >= 4) & (df_owners['count'] <= 10)])
    owner_data['owners_11_25_count'] = len(df_owners[(df_owners['count'] >= 11) & (df_owners['count'] <= 25)])
    owner_data['owners_26_50_count'] = len(df_owners[(df_owners['count'] >= 26) & (df_owners['count'] <= 50)])
    owner_data['owners_over_50_count'] = len(df_owners[df_owners['count'] >= 51])
    owner_data['top10_concentration_ratio'] = owner_data['top10_owners_count'] / (owner_data['top10_owners_count'] + owner_data['other_owners_count'])
    owner_data['singleton_ratio'] = owner_data['owners_1_count'] / owner_data['total_owners']

    return owner_data

# Nft情報を取得
def get_nft_data(data):
    extracted_data = {key: data[key] for key in ['issuer','taxon', 'totalNfts', 'totalOwners']}
    return extracted_data

# Gini係数を計算する
def get_gini_coefficient(owner_data):
    if owner_data == None:
        return None
    # Extract the counts and sort them
    counts = sorted([item['count'] for item in owner_data])

    # Calculate the cumulative counts
    cum_counts = list(accumulate(counts))

    # Calculate Lorenz curve points
    n = len(counts)
    lorenz_curve = [(0, 0)]
    for i in range(n):
        lorenz_curve.append(((i + 1) / n, cum_counts[i] / cum_counts[-1]))

    # Calculate Gini coefficient using the Lorenz curve
    gini_coefficient = 1 - 2 * sum(y for x, y in lorenz_curve) / n

    return gini_coefficient

# エントロピーを計算する
def get_entropy(owner_data):
    if owner_data == None:
        return None
    # Calculate the total count of NFTs
    total_count = sum([item['count'] for item in owner_data])
    # Calculate the probability distribution
    probabilities = [item['count'] / total_count for item in owner_data]
    # Calculate the entropy
    entropy = -sum([p * math.log2(p) for p in probabilities if p > 0])  # Avoid log(0)
    return entropy

# 書き込み
def write2db(conn,product_id,nft_data,owner_data,gini_coefficient,owners_box_plot):
    print(nft_data)
    print(owner_data)
    print(gini_coefficient)
    if owner_data == None:
        return
    try:
        cur = conn.cursor()
        insert_query = """
            INSERT INTO nft_distribution
            (nft_product_id, top10_owners, top10_owners_count, other_owners_count, total_nfts, total_owners, owners_1_count, 
            owners_2_3_count, owners_4_10_count, owners_11_25_count, owners_26_50_count, 
            owners_over_50_count,top10_concentration_ratio,singleton_ratio,gini_coefficient,owners_box_plot)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cur.execute(insert_query, (
            int(product_id),  # int() を使用して変換
            json.dumps(owner_data['top10_owners']),
            int(owner_data['top10_owners_count']),  # 同様に変換
            int(owner_data['other_owners_count']),  # 同様に変換
            int(nft_data['totalNfts']),  # 同様に変換
            int(nft_data['totalOwners']),  # 同様に変換
            int(owner_data['owners_1_count']),  # 同様に変換
            int(owner_data['owners_2_3_count']),  # 同様に変換
            int(owner_data['owners_4_10_count']),  # 同様に変換
            int(owner_data['owners_11_25_count']),  # 同様に変換
            int(owner_data['owners_26_50_count']),  # 同様に変換
            int(owner_data['owners_over_50_count']),  # 同様に変換
            owner_data['top10_concentration_ratio'],
            owner_data['singleton_ratio'],
            gini_coefficient,
            json.dumps(owners_box_plot, sort_keys=True)
        ))
        # トランザクションの確認
        conn.commit()

    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        cur.close()


db_password: str = os.environ.get("SUPABASE_PASS")
db_host: str = os.environ.get("SUPABASE_HOST")

# データベースに接続
conn = psycopg2.connect(
    dbname="postgres",
    user="postgres",
    password=db_password,
    host=db_host,
    port="5432"
)
api_urls = get_api_urls(conn)
print(api_urls)
if api_urls:
    for item in api_urls:
        data = fetch_data(item['url'])
        if data:
            write2db(conn,
            item['id'],
            get_nft_data(data),
            get_owner_data2(data),
            get_gini_coefficient(get_owner_data(data)),
            compute_boxplot_parameters(get_owner_data(data))
            )
        else:
            print('API Error:'+url)
conn.close()
