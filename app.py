import streamlit as st
import requests
import pandas as pd
import cv2
import numpy as np

# 從 Secrets 讀取網址
GAS_URL = st.secrets["GAS_URL"]

st.set_page_config(page_title="研習報到站 2.0", page_icon="✅", layout="centered")

# --- 1. 優化：加入快取機制減少 GAS 負擔 ---
@st.cache_data(ttl=20) # 資料每 20 秒自動更新一次
def fetch_data():
    try:
        response = requests.get(GAS_URL)
        return pd.DataFrame(response.json())
    except Exception as e:
        st.error(f"連線失敗: {e}")
        return pd.DataFrame()

def checkin_user(email):
    with st.spinner('同步資料庫中...'):
        response = requests.post(GAS_URL, json={"email": email})
        return response.text

# --- 2. UI 界面美化：上方進度條 ---
df_all = fetch_data()
if not df_all.empty:
    total = len(df_all)
    checked = len(df_all[df_all['報到狀態'] == "✅ 已報到"])
    percent = int((checked / total) * 100)
    
    st.title("📲 研習行動報到站")
    st.progress(checked / total)
    st.caption(f"📊 目前進度：{checked} / {total} 人 (已完成 {percent}%)")
    st.divider()

# 分頁切換
tab1, tab2, tab3 = st.tabs(["📷 QR 掃描", "🔍 手動搜尋", "📋 全員清單"])

with tab1:
    img = st.camera_input("請拍下 QR Code")
    if img:
        # QR Code 辨識邏輯保持不變...
        bytes_data = img.getvalue()
        cv_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
        detector = cv2.QRCodeDetector()
        email, _, _ = detector.detectAndDecode(cv_img)
        
        if email:
            user = df_all[df_all['電子郵件'] == email]
            if not user.empty:
                st.success(f"📍 找到對象：{user.iloc[0]['姓名']}")
                if user.iloc[0]['報到狀態'] == "✅ 已報到":
                    st.warning("此人員已於先前完成報到。")
                elif st.button("確認報到", type="primary"):
                    res = checkin_user(email)
                    if res == "Success":
                        st.toast(f"{email} 報到成功！", icon='🎉')
                        st.cache_data.clear() # 報到成功後強制清除快取
                        st.rerun()
            else:
                st.error("查無此 Email，請確認 QR Code 內容。")

with tab2:
    search = st.text_input("輸入關鍵字搜尋 (姓名/單位/電話)")
    if search:
        # 全欄位關鍵字搜尋
        res = df_all[df_all.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)]
        
        if not res.empty:
            st.dataframe(res[['姓名', '單位', '報到狀態', '連絡電話']], use_container_width=True)
            target = st.selectbox("請選擇報到對象", res['電子郵件'].tolist())
            
            if st.button("手動報到", key="manual_btn"):
                res_status = checkin_user(target)
                if res_status == "Success":
                    st.success(f"{target} 報到成功！")
                    st.cache_data.clear()
                    st.rerun()
        else:
            st.warning("查無相關資料")

with tab3:
    st.subheader("完整名單預覽")
    st.dataframe(df_all[['姓名', '單位', '報到狀態']], use_container_width=True)