import streamlit as st
import requests
import pandas as pd

# --- 1. 基礎設定 ---
# 請確保 Streamlit Cloud 的 Secrets 中已設定 GAS_URL
GAS_URL = st.secrets.get("GAS_URL", "")
st.set_page_config(page_title="研習報到站", page_icon="📝", layout="centered")

# --- 2. 資料獲取 (從 GAS API 抓取 JSON) ---
@st.cache_data(ttl=5)
def get_roster():
    if not GAS_URL: return pd.DataFrame()
    try:
        # 加上 ?action=getData 參數來觸發 GAS 回傳 JSON
        res = requests.get(f"{GAS_URL}?action=getData")
        if res.status_code == 200:
            df = pd.DataFrame(res.json()).astype(str)
            df.columns = df.columns.str.strip() # 清理欄位標題空格
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"連線失敗：{e}")
        return pd.DataFrame()

# --- 3. UI 介面 ---
st.title("📲 研習行動報到站")
df_all = get_roster()

tab1, tab2, tab3 = st.tabs(["📷 掃描報到", "🔍 手動報到", "📋 名單預覽"])

# -- Tab 1: 嵌入 GAS 掃描網頁 (解決相機權限報錯) --
with tab1:
    st.info("💡 提示：若手機彈出權限視窗，請務必點選「允許」以開啟相機。")
    
    # 【關鍵修正】：因為 st.iframe 不支援 allow 參數，我們手動寫 HTML 標籤
    # 加入 allow="camera; microphone" 確保瀏覽器授權相機
    iframe_html = f"""
        <iframe 
            src="{GAS_URL}" 
            width="100%" 
            height="550" 
            style="border:none;" 
            allow="camera; microphone"
        ></iframe>
    """
    
    # 使用 st.components.v1.html 來嵌入這段自定義的 iframe
    st.components.v1.html(iframe_html, height=560)

# -- Tab 2: 手動報到 --
with tab2:
    st.subheader("🔍 搜尋姓名報到")
    search_q = st.text_input("請輸入姓名或關鍵字")
    
    if search_q and not df_all.empty:
        # 過濾包含關鍵字的資料
        mask = df_all.apply(lambda r: r.str.contains(search_q, case=False).any(), axis=1)
        res = df_all[mask]
        
        if not res.empty:
            options = []
            id_map = {}
            for _, row in res.iterrows():
                # 建立易讀的標籤，自動適應欄位名稱
                name_val = row.get('姓名', '未知')
                unit_val = row.get('單位', '--')
                status_val = row.get('報到狀態', '')
                id_val = row.get('隨機ID', '')
                
                label = f"{name_val} | {unit_val} | {status_val}"
                options.append(label)
                id_map[label] = (id_val, name_val)
            
            selected = st.selectbox("請選擇人員：", options)
            if st.button("執行手動報到", type="primary"):
                tid, tname = id_map[selected]
                with st.spinner("同步至試算表中..."):
                    # POST 到 GAS 執行報到邏輯
                    post_res = requests.post(GAS_URL, json={"id": tid})
                    if post_res.text == "Success":
                        st.success(f"✅ {tname} 手動報到成功！")
                        st.cache_data.clear() # 清除快取以刷新名單
                        st.rerun()
                    else:
                        st.warning(f"結果：{post_res.text}")
        else:
            st.warning("查無相關資料。")

# -- Tab 3: 名單預覽 --
with tab3:
    if not df_all.empty:
        # 只顯示關鍵欄位
        display_cols = [c for c in ['姓名', '單位', '報到狀態', '隨機ID'] if c in df_all.columns]
        st.dataframe(df_all[display_cols], width="stretch")
        if st.button("🔄 重新整理資料"):
            st.cache_data.clear()
            st.rerun()