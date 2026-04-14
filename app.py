import streamlit as st
import requests
import pandas as pd

# --- 1. 設定與金鑰讀取 ---
# 確保 Streamlit Cloud Secrets 中有名稱為 GAS_URL 的設定
GAS_URL = st.secrets.get("GAS_URL", "")

st.set_page_config(page_title="研習報到系統", page_icon="📝", layout="centered")

# --- 2. 資料獲取函式 ---
@st.cache_data(ttl=5)
def fetch_data():
    if not GAS_URL:
        return pd.DataFrame()
    try:
        # 加上 action=getData 參數觸發 GAS 回傳 JSON
        res = requests.get(f"{GAS_URL}?action=getData")
        if res.status_code == 200:
            df = pd.DataFrame(res.json()).astype(str)
            df.columns = df.columns.str.strip() # 清除欄位標頭空格
            return df
        return pd.DataFrame()
    except:
        return pd.DataFrame()

# --- 3. UI 主介面 ---
st.title("📲 研習行動報到站")
df_all = fetch_data()

# 分頁標籤
tab1, tab2, tab3 = st.tabs(["📷 掃描報到", "🔍 手動報到", "📋 名單預覽"])

# --- Tab 1: 掃描報到 (終極解決方案：跳脫框架) ---
with tab1:
    st.subheader("📷 行動掃描報到")
    
    # 說明文字
    st.warning("由於瀏覽器安全限制，請點擊下方按鈕開啟專屬掃描視窗。")
    
    # 建立一個醒目的連結按鈕
    # 利用 markdown 語法做出像按鈕的樣式
    st.markdown(f"""
        <a href="{GAS_URL}" target="_blank" style="text-decoration: none;">
            <div style="
                background-color: #28a745;
                color: white;
                padding: 15px;
                text-align: center;
                border-radius: 10px;
                font-size: 20px;
                font-weight: bold;
                margin: 20px 0;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            ">
                🚀 點我開啟相機掃描器
            </div>
        </a>
    """, unsafe_allow_html=True)
    
    st.info("💡 掃描成功後，您可以直接關閉掃描視窗，回到此處查看報到進度。")
    
    # 保留一個備用的嵌入視窗 (萬一某些瀏覽器支援)
    with st.expander("若您的手機支援，也可嘗試直接在此掃描"):
        iframe_html = f'<iframe src="{GAS_URL}" width="100%" height="500" allow="camera; microphone; camera *;" style="border:none;"></iframe>'
        st.components.v1.html(iframe_html, height=520)


# -- Tab 2: 手動報到 (您提到功能正確) --
with tab2:
    st.subheader("🔍 手動搜尋報到")
    search_q = st.text_input("請輸入姓名關鍵字")
    
    if search_q and not df_all.empty:
        mask = df_all.apply(lambda r: r.str.contains(search_q, case=False).any(), axis=1)
        res = df_all[mask]
        
        if not res.empty:
            options = []
            id_map = {}
            for _, row in res.iterrows():
                # 自動抓取欄位，若名稱不符則顯示 ID
                name = row.get('姓名', '未知')
                id_val = row.get('隨機ID', '')
                label = f"{name} | {row.get('單位','--')} | {row.get('報到狀態','')}"
                options.append(label)
                id_map[label] = (id_val, name)
            
            selected = st.selectbox("請選擇報到對象：", options)
            if st.button("確認報到", type="primary"):
                tid, tname = id_map[selected]
                with st.spinner("更新中..."):
                    post_res = requests.post(GAS_URL, json={"id": tid})
                    if post_res.text == "Success":
                        st.success(f"✅ {tname} 報到成功！")
                        st.cache_data.clear() # 重新抓取資料
                    else:
                        st.warning(f"結果：{post_res.text}")
        else:
            st.warning("查無此人。")

# -- Tab 3: 名單預覽 --
with tab3:
    if not df_all.empty:
        # 過濾顯示欄位
        show_cols = [c for c in ['姓名', '單位', '報到狀態', '隨機ID'] if c in df_all.columns]
        st.dataframe(df_all[show_cols], width="stretch")
        if st.button("🔄 刷新名單"):
            st.cache_data.clear()
            st.rerun()