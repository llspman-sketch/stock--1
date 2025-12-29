import os
import pandas as pd
from FinMind.data import DataLoader
from datetime import datetime, timedelta
import time

def get_last_trading_day():
    # 強制設定為上週五，先確保有資料可以測試
    # 今天是 2025-12-29 (週一)，最近的交易日是 2025-12-26 (週五)
    return "2025-12-26"

def run_analysis():
    token = os.getenv('FINMIND_TOKEN')
    print(f"DEBUG: 檢查 Token 是否存在: {'是' if token else '否'}")
    
    dl = DataLoader()
    if token:
        try:
            dl.login(api_token=token)
            print("DEBUG: Token 登入指令已執行")
        except Exception as e:
            print(f"DEBUG: 登入發生錯誤: {e}")

    target_date = get_last_trading_day()
    print(f"📡 準備抓取日期: {target_date}")

    target_brokers = ['凱基-城中', '統一-城中', '元大-城中', '凱基-台北', '凱基-松山', '富邦-建國', '美林', '摩根大通']

    try:
        # 使用 try-except 包住 API 請求，防止它因為 KeyError['data'] 崩潰
        print("DEBUG: 正在請求全市場報表...")
        try:
            df_price = dl.taiwan_stock_trading_daily_report(date=target_date)
        except Exception as api_err:
            return f"<h1>API 請求失敗</h1><p>詳細訊息: {api_err}</p><p>這通常是 Token 無效或當日請求次數 (超過 300 次) 已滿。</p>"

        if df_price is None or df_price.empty:
            return f"<h1>{target_date} 找不到資料</h1><p>請確認該日是否為國定假日。</p>"

        # 篩選漲停
        # 這裡根據可能的欄位名稱做彈性判斷
        if 'spread' in df_price.columns:
            df_price['change_rate'] = df_price['spread'] / (df_price['close'] - df_price['spread'])
            limit_up = df_price[df_price['change_rate'] >= 0.09]
        else:
            limit_up = df_price.head(10) # 萬一抓不到漲幅，先抓前10檔測試

        stock_list = limit_up['stock_id'].tolist()
        print(f"📊 找到 {len(stock_list)} 檔待檢查個股")

        results = []
        # 為了節省次數，我們只測前 5 檔
        for stock_id in stock_list[:5]:
            print(f"DEBUG: 正在檢查 {stock_id} 的分點...")
            try:
                df_chips = dl.taiwan_stock_broker_analysis(stock_id=stock_id, start_date=target_date, end_date=target_date)
                if df_chips is not None and not df_chips.empty:
                    hits = df_chips[df_chips['broker_name'].isin(target_brokers)].copy()
                    if not hits.empty:
                        hits['net_buy'] = hits['buy'] - hits['sell']
                        for _, row in hits[hits['net_buy'] > 10].iterrows():
                            results.append({"股票": stock_id, "分點": row['broker_name'], "買超": int(row['net_buy'])})
                time.sleep(1) # 稍微停頓避免被鎖
            except:
                continue

        if results:
            html_table = pd.DataFrame(results).to_html(classes='table table-dark table-striped', index=False)
        else:
            html_table = f"<div class='alert alert-info'>{target_date} 漲停股中沒看到指定大戶。</div>"

        return f"<html><body style='background:#121212;color:white;padding:30px;'><h1>分析結果 ({target_date})</h1>{html_table}</body></html>"

    except Exception as e:
        return f"<h1>程式邏輯錯誤</h1><p>{str(e)}</p>"

if __name__ == "__main__":
    content = run_analysis()
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(content)
