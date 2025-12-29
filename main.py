import os
import pandas as pd
from FinMind.data import DataLoader
from datetime import datetime, timedelta

def run_analysis():
    # 讀取 GitHub Secrets 裡的 Token
    token = os.getenv('FINMIND_TOKEN')
    dl = DataLoader()
    
    # 修正登入指令
    if token:
        try:
            # 這是目前的正確指令：api_token
            dl.login(api_token=token)
        except Exception as e:
            print(f"Token 登入失敗: {e}，將嘗試以匿名模式繼續")

    # 設定抓取日期 (考慮台灣時區 UTC+8)
    # 如果現在不到晚上 6:30，我們就抓前一天的資料
    now_tw = datetime.utcnow() + timedelta(hours=8)
    if now_tw.hour < 18 or (now_tw.hour == 18 and now_tw.minute < 30):
        target_date = (now_tw - timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        target_date = now_tw.strftime("%Y-%m-%d")
    
    print(f"📡 正在分析日期: {target_date}")

    # 目標分點：包含城中幫、凱基台北等
    target_brokers = ['凱基-城中', '統一-城中', '元大-城中', '凱基-台北', '凱基-松山', '富邦-建國', '美林', '摩根大通']

    try:
        # 1. 抓取當日行情
        df_price = dl.taiwan_stock_daily_info(date=target_date)
        
        if df_price is None or df_price.empty:
            return f"<h1>{target_date} 目前尚無盤後數據</h1><p>請等待 18:30 資料更新後再試。</p>"

        # 2. 篩選漲停 (漲幅 >= 9.8% 且收盤等於最高價)
        limit_up = df_price[(df_price['close'] >= df_price['last_close'] * 1.098)]
        stock_list = limit_up['stock_id'].tolist()
        
        print(f"📊 找到 {len(stock_list)} 檔漲停股")

        results = []
        for stock_id in stock_list:
            # 3. 抓取分點
            df_chips = dl.taiwan_stock_broker_analysis(stock_id=stock_id, start_date=target_date, end_date=target_date)
            
            if df_chips is not None and not df_chips.empty:
                # 過濾出我們鎖定的隔日沖分點
                hits = df_chips[df_chips['broker_name'].isin(target_brokers)].copy()
                if not hits.empty:
                    hits['net_buy'] = hits['buy'] - hits['sell']
                    # 只取淨買超 > 50 張的 (門檻可自行調整)
                    heavy_hits = hits[hits['net_buy'] > 50]
                    for _, row in heavy_hits.iterrows():
                        results.append({
                            "股票": stock_id,
                            "分點名稱": row['broker_name'],
                            "買超張數": int(row['net_buy'])
                        })

        # 4. 生成網頁內容
        if results:
            df_final = pd.DataFrame(results)
            html_table = df_final.to_html(classes='table table-striped table-dark', index=False)
        else:
            html_table = "<div class='alert alert-warning'>今日漲停股中，無指定大戶（如城中幫）大量買超跡象。</div>"

        return f"""
        <html>
        <head>
            <meta charset="utf-8">
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
            <style>body {{ background-color: #121212; color: #ffffff; padding: 50px; }}</style>
        </head>
        <body>
            <div class="container">
                <h1 class="mb-4">🔍 {target_date} 城中幫 & 隔日沖追蹤</h1>
                {html_table}
                <hr>
                <p class="text-secondary small">自動更新時間: {now_tw.strftime('%Y-%m-%d %H:%M:%S')} (台北時間)</p>
            </div>
        </body>
        </html>
        """
    except Exception as e:
        print(f"發生錯誤: {e}")
        return f"<h1>系統執行時出錯</h1><p>{str(e)}</p>"

if __name__ == "__main__":
    content = run_analysis()
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(content)
    html_result = run_analysis()
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_result)
