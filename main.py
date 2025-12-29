import os
import pandas as pd
from FinMind.data import DataLoader
from datetime import datetime, timedelta

def run_analysis():
    # 1. 讀取 Token 並登入
    token = os.getenv('FINMIND_TOKEN')
    dl = DataLoader()
    if token:
        try:
            dl.login(api_token=token)
        except Exception as e:
            print(f"登入失敗: {e}")

    # 2. 決定分析日期 (考慮台灣時區 UTC+8)
    # 如果現在不到晚上 18:30，我們就抓「前一個交易日」
    now_tw = datetime.utcnow() + timedelta(hours=8)
    if now_tw.hour < 18 or (now_tw.hour == 18 and now_tw.minute < 30):
        target_date = (now_tw - timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        target_date = now_tw.strftime("%Y-%m-%d")
    
    print(f"📡 正在分析日期: {target_date}")

    # 定義城中幫與常見隔日沖分點
    target_brokers = ['凱基-城中', '統一-城中', '元大-城中', '凱基-台北', '凱基-松山', '富邦-建國', '美林', '摩根大通']

    try:
        # 【修正重點】使用正確的報表指令獲取全市場行情
        df_price = dl.taiwan_stock_trading_daily_report(date=target_date)
        
        if df_price is None or df_price.empty:
            return f"<div class='alert alert-info'><h3>{target_date} 目前尚無盤後報表數據</h3><p>請等待台灣時間 18:30 資料更新後再試。</p></div>"

        # 3. 篩選漲停股 
        # 由於報表中通常有 'spread' (漲跌) 欄位，我們計算漲幅
        # 漲停通常為前日收盤 * 1.1，這裡簡單判斷漲幅 > 9.7%
        # 部分報表欄位為 'change' 或 'spread'，視 FinMind 傳回而定
        df_price['change_rate'] = df_price['spread'] / (df_price['close'] - df_price['spread'])
        limit_up = df_price[df_price['change_rate'] >= 0.097]
        stock_list = limit_up['stock_id'].tolist()
        
        print(f"📊 找到 {len(stock_list)} 檔漲停/強勢股")

        results = []
        for stock_id in stock_list:
            # 4. 抓取分點資料 (此部分指令目前維持穩定)
            df_chips = dl.taiwan_stock_broker_analysis(
                stock_id=stock_id, 
                start_date=target_date, 
                end_date=target_date
            )
            
            if df_chips is not None and not df_chips.empty:
                hits = df_chips[df_chips['broker_name'].isin(target_brokers)].copy()
                if not hits.empty:
                    hits['net_buy'] = hits['buy'] - hits['sell']
                    # 只取淨買超 > 50 張的大戶
                    heavy_hits = hits[hits['net_buy'] > 50]
                    for _, row in heavy_hits.iterrows():
                        results.append({
                            "股票": stock_id,
                            "分點名稱": row['broker_name'],
                            "買超張數": int(row['net_buy'])
                        })

        # 5. 生成網頁內容
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
            <style>
                body {{ background-color: #121212; color: #ffffff; padding: 50px; font-family: "Microsoft JhengHei", sans-serif; }}
                .table {{ color: white; }}
                .container {{ max-width: 800px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1 class="mb-4">🔍 {target_date} 城中幫 & 隔日沖監控</h1>
                {html_table}
                <hr>
                <p class="text-secondary small">自動分析時間: {now_tw.strftime('%Y-%m-%d %H:%M:%S')} (台北時間)</p>
                <p class="text-secondary small">監控清單：{', '.join(target_brokers)}</p>
            </div>
        </body>
        </html>
        """
    except Exception as e:
        print(f"錯誤細節: {e}")
        return f"<h1>系統分析時發生異常</h1><p>請檢查 Actions 日誌或 Token 權限。</p><p>錯誤訊息: {str(e)}</p>"

if __name__ == "__main__":
    content = run_analysis()
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(content)
        f.write(content)
    html_result = run_analysis()
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_result)
