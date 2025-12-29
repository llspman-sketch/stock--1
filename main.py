import os
import pandas as pd
from FinMind.data import DataLoader
from datetime import datetime, timedelta

def get_last_trading_day(date_obj):
    """
    根據目前時間計算最近一個有資料的交易日
    """
    # 台灣時區現在時間
    now = date_obj + timedelta(hours=8)
    
    # 如果現在是 18:30 以前，我們先看昨天
    if now.hour < 18 or (now.hour == 18 and now.minute < 30):
        check_date = now - timedelta(days=1)
    else:
        check_date = now

    # 如果 check_date 是週日(6)，退到週五
    if check_date.weekday() == 6:
        check_date -= timedelta(days=2)
    # 如果 check_date 是週六(5)，退到週五
    elif check_date.weekday() == 5:
        check_date -= timedelta(days=1)
        
    return check_date.strftime("%Y-%m-%d")

def run_analysis():
    # 1. 初始化與登入
    token = os.getenv('FINMIND_TOKEN')
    dl = DataLoader()
    if token:
        try:
            dl.login(api_token=token)
        except:
            print("Token 登入失敗")

    # 2. 取得日期 (自動避開週末)
    target_date = get_last_trading_day(datetime.utcnow())
    print(f"📡 最終決定分析日期: {target_date}")

    target_brokers = ['凱基-城中', '統一-城中', '元大-城中', '凱基-台北', '凱基-松山', '富邦-建國', '美林', '摩根大通']

    try:
        # 3. 抓取行情 (全市場報表)
        df_price = dl.taiwan_stock_trading_daily_report(date=target_date)
        
        if df_price is None or df_price.empty:
            return f"<h1>{target_date} 為休市日或無資料</h1>"

        # 4. 篩選漲停 (漲幅大於 9.7%)
        # 判斷欄位名稱 (FinMind 版本不同欄位可能略有差異)
        if 'spread' in df_price.columns and 'close' in df_price.columns:
            df_price['change_rate'] = df_price['spread'] / (df_price['close'] - df_price['spread'])
            limit_up = df_price[df_price['change_rate'] >= 0.097]
        else:
            # 備用判斷 (如果沒有 spread)
            limit_up = df_price[df_price['change'] >= 9.5] if 'change' in df_price.columns else df_price.head(0)

        stock_list = limit_up['stock_id'].tolist()
        print(f"📊 找到 {len(stock_list)} 檔強勢股")

        results = []
        # 為了避免 API 請求太頻繁，我們只分析前 30 檔最強的
        for stock_id in stock_list[:30]:
            try:
                df_chips = dl.taiwan_stock_broker_analysis(stock_id=stock_id, start_date=target_date, end_date=target_date)
                if df_chips is not None and not df_chips.empty:
                    hits = df_chips[df_chips['broker_name'].isin(target_brokers)].copy()
                    if not hits.empty:
                        hits['net_buy'] = hits['buy'] - hits['sell']
                        heavy_hits = hits[hits['net_buy'] > 50]
                        for _, row in heavy_hits.iterrows():
                            results.append({"股票": stock_id, "分點": row['broker_name'], "買超": int(row['net_buy'])})
            except:
                continue

        # 5. 輸出 HTML
        if results:
            html_table = pd.DataFrame(results).to_html(classes='table table-dark table-striped', index=False)
        else:
            html_table = f"<div class='alert alert-secondary'>今日 ({target_date}) 漲停股中無指定大戶跡象。</div>"

        return f"""
        <html>
        <head>
            <meta charset="utf-8">
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
            <style>body{{background:#121212;color:white;padding:30px;}} .table{{color:white;}}</style>
        </head>
        <body>
            <h1>🚀 隔日沖大戶監控報表</h1>
            <p>分析日期：{target_date}</p>
            {html_table}
            <p style='color:gray; font-size:12px; margin-top:20px;'>更新時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </body>
        </html>
        """
    except Exception as e:
        return f"<h1>分析發生錯誤</h1><p>可能原因：日期為假日或 API 次數達上限</p><p>錯誤代碼：{str(e)}</p>"

if __name__ == "__main__":
    content = run_analysis()
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(content)
