import streamlit as st
import requests
import pandas as pd

# --- 1. 基礎設定 ---
GAS_URL = st.secrets.get("GAS_URL", "")
st.set_page_config(page_title="研習報到站", page_icon="📝", layout="centered")

# --- 2. 資料獲取 (使用同一個 GAS 網址 + 參數) ---
@st.cache_data(ttl=5)
def get_roster():
    if not GAS_URL: return pd.DataFrame()
    try:
        # 向 GAS 請求 JSON 資料
        res = requests.get(f"{GAS_URL}?action=getData")
        if res.status_code == 200:
            df = pd.DataFrame(res.json()).astype(str)
            df.columns = df.columns.str.strip() # 清理欄位空格
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"連線失敗：{e}")
        return pd.DataFrame()

# --- 3. UI 介面 ---
st.title("📲 研習行動報到站")
df_all = get_roster()

tab1, tab2, tab3 = st.tabs(["📷 掃描報到", "🔍 手動報到", "📋 名單預覽"])

# -- Tab 1: 嵌入 GAS 掃描網頁 (穩定性最高) --
with tab1:
    st.info("💡 提示：若手機彈出權限視窗，請務必點選「允許」以開啟相機。")
    
    # 【關鍵修正】：加入 allow="camera" 屬性
    st.components.v1.iframe(
        GAS_URL, 
        height=550, 
        scrolling=True,
        # 這裡非常重要，必須允許 camera 權限
        allow="camera"
    )

# -- Tab 2: 手動報到 (Python 介面) --
with tab2:
    st.subheader("🔍 搜尋姓名報到")
    search_q = st.text_input("請輸入姓名或關鍵字")
    
    if search_q and not df_all.empty:
        # 過濾包含關鍵字的列
        mask = df_all.apply(lambda r: r.str.contains(search_q, case=False).any(), axis=1)
        res = df_all[mask]
        
        if not res.empty:
            # 建立選擇選單
            options = []
            id_map = {}
            for _, row in res.iterrows():
                label = f"{row['姓名']} | {row.get('單位','--')} | {row.get('報到狀態','')}"
                options.append(label)
                # 假設 ID 欄位名稱為「隨機ID」
                id_map[label] = (row['隨機ID'], row['姓名'])
            
            selected = st.selectbox("請選擇人員：", options)
            if st.button("執行手動報到", type="primary"):
                tid, tname = id_map[selected]
                with st.spinner("同步至試算表中..."):
                    post_res = requests.post(GAS_URL, json={"id": tid})
                    if post_res.text == "Success":
                        st.success(f"✅ {tname} 手動報到成功！")
                        st.cache_data.clear() # 更新快取
                    else:
                        st.warning(f"結果：{post_res.text}")
        else:
            st.warning("查無此人。")

# -- Tab 3: 名單預覽 --
with tab3:
    if not df_all.empty:
        # 動態判斷要顯示的欄位，避免 KeyError
        cols = [c for c in ['姓名', '單位', '報到狀態', '隨機ID'] if c in df_all.columns]
        st.dataframe(df_all[cols], width="stretch")
        if st.button("🔄 重新整理資料"):
            st.cache_data.clear()
            st.rerun()