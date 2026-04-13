import streamlit as st
import requests
import pandas as pd

# --- 1. 設定 ---
GAS_URL = st.secrets.get("GAS_URL", "")
st.set_page_config(page_title="研習報到系統", page_icon="📝", layout="centered")

# --- 2. 抓取資料 ---
@st.cache_data(ttl=5)
def fetch_data():
    try:
        # 使用 GAS 部署網址後加上參數，通常 GAS 需要特定的參數來觸發 JSON 回傳
        # 這裡建議在 GAS 另設一個 Web App 網址或用 doPost 觸發
        response = requests.get(GAS_URL + "?action=getData") 
        # (註：若您的 GAS 只回傳 HTML，請確保 GAS Code 內 doGet 判斷參數回傳 JSON)
        if response.status_code == 200:
            df = pd.DataFrame(response.json()).astype(str)
            df.columns = df.columns.str.strip()
            return df
        return pd.DataFrame()
    except:
        return pd.DataFrame()

# --- 3. 主介面 ---
st.title("📲 研習行動報到站")
df_all = fetch_data()

tab1, tab2, tab3 = st.tabs(["📷 掃描報到", "🔍 手動報到", "📋 名單預覽"])

# -- Tab 1: 直接嵌入 GAS 的掃描頁面 --
with tab1:
    # 這裡直接嵌入 GAS Web App 的網址，穩定性 100%
    st.components.v1.iframe(GAS_URL, height=600, scrolling=True)

# -- Tab 2: 手動報到邏輯 --
with tab2:
    st.subheader("🔍 搜尋並執行報到")
    search_q = st.text_input("輸入關鍵字 (姓名/電話)")
    
    if search_q and not df_all.empty:
        mask = df_all.apply(lambda row: row.str.contains(search_q, case=False).any(), axis=1)
        res = df_all[mask]
        
        if not res.empty:
            options = [f"{r['姓名']} | {r.get('單位','--')} | {r.get('報到狀態','')}" for _, r in res.iterrows()]
            choice = st.selectbox("請選擇人員", options)
            
            if st.button("執行手動報到", type="primary"):
                # 從顯示字串中抓取 ID (假設隨機 ID 在資料中)
                # 這裡直接使用搜尋結果的第一筆或對應資料
                target_id = res.iloc[options.index(choice)]['隨機ID']
                target_name = res.iloc[options.index(choice)]['姓名']
                
                with st.spinner("更新中..."):
                    resp = requests.post(GAS_URL, json={"id": target_id})
                    if resp.text == "Success":
                        st.success(f"✅ {target_name} 報到成功")
                        st.cache_data.clear()
                    else:
                        st.warning(f"結果：{resp.text}")
        else:
            st.warning("查無資料")

# -- Tab 3: 名單預覽 --
with tab3:
    if not df_all.empty:
        cols = [c for c in ['姓名', '單位', '報到狀態', '隨機ID'] if c in df_all.columns]
        st.dataframe(df_all[cols], width="stretch")
        if st.button("🔄 重新整理"):
            st.cache_data.clear()
            st.rerun()