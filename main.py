import os
import pandas as pd
from FinMind.data import DataLoader
from datetime import datetime

# 1. 初始化 FinMind (從 GitHub Secrets 讀取 Token)
token = os.getenv('FINMIND_TOKEN')
dl = DataLoader()
if token:
    dl.login_token(token)

def run_analysis():
    # 取得今天日期
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 定義目標分點 (城中幫與常見隔日沖)
    target_brokers = ['凱基-城中', '統一-城中', '元大-城中', '凱基-台北', '凱基-松山', '富邦-建國', '美林', '摩根大通']

    # A. 抓取全市場行情
    try:
        df_price = dl.taiwan_stock_daily_info(date=today)
    except:
        return f"<h1>{today} 尚未更新數據或非交易日</h1>"

    if df_price.empty:
        return f"<h1>{today} 目前查無交易資料</h1>"

    # B. 篩選漲停股 (漲幅 > 9.8% 且 收在最高)
    limit_up = df_price[((df_price['close'] - df_price['last_close']) / df_price['last_close'] >= 0.098)]
    stock_list = limit_up['stock_id'].tolist()
    
    results = []
    for stock_id in stock_list:
        # C. 抓取分點資料
        df_chips = dl.taiwan_stock_broker_analysis(stock_id=stock_id, start_date=today, end_date=today)
        if df_chips.empty: continue
        
        # D. 比對指定分點
        hits = df_chips[df_chips['broker_name'].isin(target_brokers)].copy()
        if not hits.empty:
            hits['net_buy'] = hits['buy'] - hits['sell']
            heavy_hits = hits[hits['net_buy'] > 100] # 門檻：買超100張
            
            for _, row in heavy_hits.iterrows():
                results.append({
                    "股票": stock_id,
                    "大戶分點": row['broker_name'],
                    "買超張數": int(row['net_buy'])
                })

    # E. 建立 HTML 內容
    html_template = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>台股隔日沖監控</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    </head>
    <body class="bg-light">
        <div class="container mt-5">
            <h1 class="mb-4">🚀 {today} 隔日沖大戶鎖漲停追蹤</h1>
            <div class="card shadow">
                <div class="card-body">
                    {pd.DataFrame(results).to_html(classes='table table-hover', index=False) if results else "今日無大戶鎖漲停跡象。"}
                </div>
            </div>
            <p class="mt-3 text-muted">註：資料每日 18:30 自動更新。分點包含：城中幫、凱基台北、富邦建國、美林等。</p>
        </div>
    </body>
    </html>
    """
    return html_template

if __name__ == "__main__":
    html_result = run_analysis()
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_result)
