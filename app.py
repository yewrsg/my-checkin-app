import streamlit as st
import requests
import pandas as pd
from streamlit_qr_scanner import qr_scanner # 引入即時掃描套件

# --- 基礎設定 ---
GAS_URL = st.secrets["GAS_URL"]

st.set_page_config(page_title="研習行動報到站", page_icon="📝", layout="centered")

# --- 資料讀取 (快取 15 秒) ---
@st.cache_data(ttl=15)
def fetch_data():
    try:
        response = requests.get(GAS_URL)
        if response.status_code == 200:
            return pd.DataFrame(response.json())
        return pd.DataFrame()
    except:
        return pd.DataFrame()

# --- 執行報到 ---
def checkin_user(rid):
    with st.spinner('同步中...'):
        try:
            response = requests.post(GAS_URL, json={"id": rid})
            return response.text
        except Exception as e:
            return f"Error: {e}"

# --- UI 介面 ---
df_all = fetch_data()

st.title("📲 研習行動報到站")

# 顯示進度條
if not df_all.empty:
    total = len(df_all)
    status_col = '報到狀態' if '報到狀態' in df_all.columns else None
    checked = len(df_all[df_all[status_col] == "✅ 已報到"]) if status_col else 0
    percent = int((checked / total) * 100) if total > 0 else 0
    st.progress(checked / total if total > 0 else 0)
    st.caption(f"📊 目前進度：{checked} / {total} 人 (已完成 {percent}%)")

st.divider()

tab1, tab2, tab3 = st.tabs(["📷 自動掃描", "🔍 手動搜尋", "📋 名單預覽"])

# -- Tab 1: 即時自動掃描 --
with tab1:
    st.subheader("請將 QR Code 對準鏡頭")
    
    # 使用即時掃描元件，不必點擊拍照按鈕
    scanned_id = qr_scanner(key="qr_scanner")
    
    # 當偵測到 QR Code 內容時
    if scanned_id:
        st.info(f"掃描結果：{scanned_id}")
        
        id_col = '隨機ID' if '隨機ID' in df_all.columns else None
        if id_col:
            user = df_all[df_all[id_col] == scanned_id]
            if not user.empty:
                name_val = user.iloc[0]['姓名']
                st.success(f"📍 找到對象：{name_val}")
                
                # 檢查報到狀態
                if status_col and user.iloc[0][status_col] == "✅ 已報到":
                    st.warning("⚠️ 提醒：此人員已完成報到。")
                    if st.button("掃描下一個人"):
                        st.rerun()
                else:
                    # 為了保險起見，我們保留一個確認按鈕，
                    # 避免鏡頭晃過某人名牌就「誤報到」。
                    # 若您希望連點都不必點，可以直接執行 checkin_user 並 rerun。
                    if st.button(f"確認【{name_val}】報到", type="primary"):
                        res = checkin_user(scanned_id)
                        if res == "Success":
                            st.balloons()
                            st.success(f"{name_val} 報到成功！")
                            st.cache_data.clear()
                            # 延遲一下讓使用者看見成功訊息，或直接重新整理
                            st.rerun()
            else:
                st.error(f"資料庫查無此 ID：{scanned_id}")
                if st.button("重試"):
                    st.rerun()

# -- Tab 2: 手動搜尋 (保持不變) --
with tab2:
    search = st.text_input("輸入關鍵字搜尋 (姓名/單位/電話)")
    if search and not df_all.empty:
        res = df_all[df_all.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)]
        if not res.empty:
            display_cols = [c for c in ['姓名', '單位', '報到狀態', '隨機ID'] if c in res.columns]
            st.dataframe(res[display_cols], use_container_width=True)
            
            if '隨機ID' in res.columns:
                target_id = st.selectbox("請選擇報到對象", res['隨機ID'].tolist())
                if st.button("手動確認報到", key="manual_btn"):
                    res_status = checkin_user(target_id)
                    if res_status == "Success":
                        st.success("手動報到成功！")
                        st.cache_data.clear()
                        st.rerun()
        else:
            st.warning("查無相關資料。")

# -- Tab 3: 名單預覽 (保持不變) --
with tab3:
    st.subheader("📋 完整名單預覽")
    if not df_all.empty:
        desired = ['姓名', '單位', '報到狀態', '隨機ID']
        available = [col for col in desired if col in df_all.columns]
        st.dataframe(df_all[available], use_container_width=True)