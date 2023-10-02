import os
import requests
import psycopg2
from psycopg2 import extras
import json
from urllib.parse import urlencode


target_list = []
item = {'issuer':'r4BEmxETRgp4UxVFM7zqQKFZzpVybdwDs7','taxon':1}
target_list.append(item)

# 環境変数からAPIトークンを取得
bithomp_token: str = os.environ.get("BITHOMP_TOKEN")
db_password: str = os.environ.get("SUPABASE_PASS")
db_host: str = os.environ.get("SUPABASE_HOST")


class NFToken:
    def __init__(self):
        self.nft_id = ''
        self.issuer = ''
        self.taxon = 0
        self.uri = ''
        self.url = ''
        self.meta = {}
        self.meta_image = ''
        self.meta_name = ''

    def set(self, nft_id, issuer, taxon, uri, url, metadata):
        self.nft_id = nft_id
        self.issuer = issuer
        self.taxon = taxon
        self.uri = uri
        self.url = url
        self.meta = metadata
        self.meta_image = metadata.get('image','')
        self.meta_name = metadata.get('name','')

    def debug_print(self):
        print('--------------------')
        print(self.nft_id)
        print(self.issuer)
        print(self.taxon)
        print(self.uri)
        print(self.url)
        print(self.meta)
        print(self.meta_image)
        print(self.meta_name)
        print('--------------------')

# フェッチ
def fetch_data(target):
    headers = {
        "x-bithomp-token": bithomp_token
    }
    base_url = 'https://bithomp.com/api/v2/nfts'
    params = urlencode(target)
    url = f"{base_url}?{params}"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error with status code: {response.status_code}")
        print(response.json())
        return None

# パース
def parse_data(nfts):
    #print(nfts)
    token_list = []
    for nft in nfts:
        token = NFToken()
        token.set(nft['nftokenID'],nft['issuer'],nft['nftokenTaxon'],nft['uri'],nft['url'],nft['metadata'])
        token_list.append(token)
    return token_list

# 書き込み
def write2db(conn,token):
    if token == None:
        return
    try:
        cur = conn.cursor()
        insert_query = """
            INSERT INTO nftokens
            (nft_id, issuer, taxon, url, uri, meta_name, meta_image)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cur.execute(insert_query, (
            token.nft_id,
            token.issuer,
            int(token.taxon),
            token.url,
            token.uri,
            token.meta_name,
            token.meta_image
        ))
        conn.commit()
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        cur.close()

# データベースに接続
conn = psycopg2.connect(
    dbname="postgres",
    user="postgres",
    password=db_password,
    host=db_host,
    port="5432"
)

if target_list:
    for target in target_list:
        data = fetch_data(target)
        if data:
            if 'nfts' in data:
                token_list = parse_data(data['nfts'])
                for token in token_list:
                    token.debug_print()
                    write2db(conn,token)
        else:
            print(f'API Error: {target}')
conn.close()
