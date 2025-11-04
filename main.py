import os
import requests
import json
from urllib.parse import urlencode, parse_qs
from flask import Flask, jsonify, request

# ⚠️ 注意: Node.js APIが稼働しているURLを設定してください
NODE_API_BASE_URL = os.environ.get("NODE_API_BASE_URL", "http://localhost:3000/api")
print(f"NODE_API_BASE_URL:{NODE_API_BASE_URL}")

# GitHubの設定ファイルURL
CONFIG_URL = 'https://raw.githubusercontent.com/siawaseok3/wakame/master/video_config.json'
print(f"CONFIG_URL:{CONFIG_URL}")

app = Flask(__name__)

# --- ヘルパー関数1: Iframeのパラメータを取得し整形する ---
def get_iframe_params():
    """
    GitHubから設定ファイルを読み込み、フロントエンドのJSロジックに従って
    整形されたパラメータ文字列を生成します。
    """
    try:
        # 1. GitHubから設定ファイルをフェッチ
        response = requests.get(CONFIG_URL)
        print(f"config_status_code:{response.status_code}")
        response.raise_for_status()
        config_data = response.json()
        
        # 2. 'params'文字列を取得
        params_string = config_data.get('params', '')
        
        if not params_string:
            return ""

        # 3. '&amp;' を '&' に置換 (JSロジックを再現)
        params_string = params_string.replace('&amp;', '&')
        
        # 4. パースとクリーンアップ
        if params_string.startswith('?'):
             params_string = params_string[1:]
        
        # parse_qsでパラメータをパース（自動でURLデコードされる）
        parsed_params = parse_qs(params_string)
        
        # parse_qsの結果は値がリストになるため、単一の値を持つ辞書に変換
        cleaned_params = {k: v[-1] for k, v in parsed_params.items()}

        # 5. 最終的なパラメータ文字列を生成
        final_params_string = urlencode(cleaned_params)
        print(f"final_params_string:?{final_params_string}")
        
        return f"?{final_params_string}" if final_params_string else ""

    except requests.exceptions.RequestException as e:
        print(f"GitHub設定ファイルの取得に失敗: {e}")
        # 失敗時はパラメータなしの空文字列を返す
        return "" 

    except Exception as e:
        print(f"設定ファイル処理エラー: {e}")
        return ""

# --- ヘルパー関数2: 必要最低限のメタデータを抽出する ---
def extract_metadata(raw_data, video_id, params_string):
    """
    Node.js APIから取得したJSONから、必要な動画メタデータとIframeリンクを抽出・生成します。
    """
    primary_info = raw_data.get('primary_info', {})
    
    # 必要な情報の抽出とIframeリンクの生成
    metadata = {
        # --- メタデータ ---
        "title": primary_info.get('title', {}).get('text'),
        "view_count": primary_info.get('view_count', {}).get('view_count', {}).get('text'),
        "published_date": primary_info.get('published', {}).get('text'),
        "relative_date": primary_info.get('relative_date', {}).get('text'),
        
        # --- Iframe リンク (動画ID + 整形済みパラメータ) ---
        "iframelink": f"https://www.youtubeeducation.com/embed/{video_id}{params_string}"
    }
    
    # Noneのキーを削除
    cleaned_metadata = {k: v for k, v in metadata.items() if v is not None}
    return cleaned_metadata

# --- 動画詳細メタデータ API エンドポイント ---
@app.route('/video_meta', methods=['GET'])
def get_video_metadata():
    video_id = request.args.get('id')
    print(f"video_id:{video_id}")
    
    if not video_id:
        return jsonify({"error": "Missing video id"}), 400

    # 1. Iframeのパラメータを先に取得・整形
    iframe_params = get_iframe_params()
    print(f"iframe_params:{iframe_params}")

    # 2. Node.js APIから動画メタデータを取得
    node_url = f"{NODE_API_BASE_URL}/video"
    print(f"node_url:{node_url}")
    
    try:
        response = requests.get(node_url, params={'id': video_id})
        print(f"response.status_code:{response.status_code}")
        response.raise_for_status()
        raw_data = response.json()
        
    except requests.exceptions.RequestException as e:
        print(f"Node.js API Request Failed: {e}")
        return jsonify({"error": "Failed to fetch data from Node.js API"}), 503
    
    except Exception as e:
        print(f"JSON or Other Error: {e}")
        return jsonify({"error": "Data processing error"}), 500

    # 3. メタデータと整形済みIframeパラメータを結合
    cleaned_meta = extract_metadata(raw_data, video_id, iframe_params)

    # 整形されたJSONデータをクライアントに返す
    return jsonify(cleaned_meta), 200

# --- アプリケーション実行 ---
if __name__ == '__main__':
    app.run(debug=True, port=5000)
