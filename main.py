import os
import requests
import pandas as pd
from datetime import datetime

def run_analysis():
    token = os.getenv('FINMIND_TOKEN')
    # 測試日期設為上週五
    target_date = "2025-12-26" 
    
    if not token:
        return "<h1>錯誤：抓不到 Token</h1><p>請檢查 GitHub Secrets 是否設定為 FINMIND_TOKEN</p>"

    # 1. 測試 API 連線並取得全市場報表 (直接使用 API 網址)
    api_url = f"https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockTradingDailyReport&date={target_date}&token={token}"
    
    try:
        response = requests.get(api_url)
        data_json = response.json()
        
        # 診斷：如果伺服器回傳不是 200 或沒資料
        if data_json.get('msg') != 'success':
            return f"""
            <h1>API 伺服器回報錯誤</h1>
            <p>狀態碼: {data_json.get('status')}</p>
            <p>錯誤訊息: {data_json.get('msg')}</p>
            <p>這代表你的 Token 可能無效或是今日 300 次額度已用完。</p>
            """
        
        # 2. 處理資料
        df_price = pd.DataFrame(data_json['data'])
        if df_price.empty:
            return f"<h1>日期 {target_date} 沒資料</h1>"

        # 3. 篩選漲幅 > 9% 的股票
        df_price['spread'] = pd.to_numeric(df_price['spread'])
        df_price['close'] = pd.to_numeric(df_price['close'])
        df_price['change_rate'] = df_price['spread'] / (df_price['close'] - df_price['spread'])
        limit_up = df_price[df_price['change_rate'] >= 0.09].copy()
        
        stock_list = limit_up['stock_id'].tolist()
        
        # 4. 抓取分點資料 (只抓前 3 檔測試，節省額度)
        target_brokers = ['凱基-城中', '統一-城中', '元大-城中', '凱基-台北', '凱基-松山', '富邦-建國', '美林', '摩根大通']
        results = []
        
        for stock_id in stock_list[:3]:
            chip_url = f"https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockBrokerAnalysis&stock_id={stock_id}&date={target_date}&token={token}"
            chip_res = requests.get(chip_url).json()
            if chip_res.get('msg') == 'success':
                df_chips = pd.DataFrame(chip_res['data'])
                hits = df_chips[df_chips['broker_name'].isin(target_brokers)].copy()
                if not hits.empty:
                    hits['net_buy'] = hits['buy'] - hits['sell']
                    for _, row in hits[hits['net_buy'] > 50].iterrows():
                        results.append({"股票": stock_id, "分點": row['broker_name'], "買超": int(row['net_buy'])})

        # 5. 生成 HTML
        res_table = pd.DataFrame(results).to_html(classes='table table-dark', index=False) if results else "今日強勢股中無大戶跡象。"
        return f"<html><body style='background:#121212;color:white;padding:30px;'><h1>分析結果 ({target_date})</h1>{res_table}</body></html>"

    except Exception as e:
        return f"<h1>連線發生異常</h1><p>{str(e)}</p>"

if __name__ == "__main__":
    content = run_analysis()
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(content)
