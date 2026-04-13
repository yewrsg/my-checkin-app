import streamlit as st
import requests
import pandas as pd
import cv2
import numpy as np

# --- 0. 基礎設定 ---
# 請確保在 Streamlit Cloud 的 Secrets 中設定了 GAS_URL
GAS_URL = st.secrets["GAS_URL"]

st.set_page_config(page_title="研習報到系統 2.0", page_icon="✅", layout="centered")

# --- 1. 資料讀取函式 (加入快取機制) ---
@st.cache_data(ttl=15) # 每 15 秒自動刷新
def fetch_data():
    try:
        response = requests.get(GAS_URL)
        if response.status_code == 200:
            return pd.DataFrame(response.json())
        else:
            st.error("無法取得資料，請檢查 GAS 部署網址是否正確。")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"連線異常: {e}")
        return pd.DataFrame()

# --- 2. 報到執行函式 ---
def checkin_user(email):
    with st.spinner('同步資料庫中...'):
        try:
            response = requests.post(GAS_URL, json={"email": email})
            return response.text
        except Exception as e:
            return f"Error: {e}"

# --- 3. 畫面標題與進度條 (動態檢查) ---
df_all = fetch_data()

st.title("📲 研習行動報到站")

if not df_all.empty:
    total = len(df_all)
    # 動態檢查「報到狀態」欄位是否存在
    status_col = '報到狀態' if '報到狀態' in df_all.columns else None
    
    if status_col:
        checked = len(df_all[df_all[status_col] == "✅ 已報到"])
    else:
        checked = 0
        st.warning("提醒：試算表中找不到『報到狀態』欄位，無法計算進度。")
    
    # 防止除以零
    percent = int((checked / total) * 100) if total > 0 else 0
    st.progress(checked / total if total > 0 else 0)
    st.caption(f"📊 目前進度：{checked} / {total} 人 (已完成 {percent}%)")
else:
    st.info("目前尚無報名資料，或資料正在載入中...")

st.divider()

# --- 4. 功能分頁 ---
tab1, tab2, tab3 = st.tabs(["📷 QR 掃描", "🔍 手動搜尋", "📋 全員清單"])

# -- Tab 1: QR 掃描 --
with tab1:
    img = st.camera_input("請拍下參加者的 QR Code")
    if img:
        bytes_data = img.getvalue()
        cv_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
        detector = cv2.QRCodeDetector()
        email, _, _ = detector.detectAndDecode(cv_img)
        
        if email:
            # 檢查 Email 欄位是否存在
            email_col = '電子郵件' if '電子郵件' in df_all.columns else None
            
            if email_col:
                user = df_all[df_all[email_col] == email]
                if not user.empty:
                    name_val = user.iloc[0]['姓名'] if '姓名' in df_all.columns else email
                    st.success(f"📍 找到對象：{name_val}")
                    
                    # 檢查報到狀態
                    if status_col and user.iloc[0][status_col] == "✅ 已報到":
                        st.warning("此人員已於先前完成報到。")
                    else:
                        if st.button("確認報到", type="primary"):
                            res = checkin_user(email)
                            if res == "Success":
                                st.toast(f"{name_val} 報到成功！", icon='🎉')
                                st.cache_data.clear() # 報到成功後清除快取
                                st.rerun()
                else:
                    st.error(f"查無此對象 ({email})，請重新確認。")
            else:
                st.error("資料庫缺少『電子郵件』欄位。")

# -- Tab 2: 手動搜尋 --
with tab2:
    search = st.text_input("輸入關鍵字搜尋 (姓名/單位/電話)")
    if search and not df_all.empty:
        # 全欄位搜尋
        res = df_all[df_all.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)]
        
        if not res.empty:
            # 動態選擇顯示欄位
            display_cols = [c for c in ['姓名', '單位', '報到狀態', '連絡電話'] if c in res.columns]
            st.dataframe(res[display_cols], use_container_width=True)
            
            if '電子郵件' in res.columns:
                target_email = st.selectbox("請選擇報到對象", res['電子郵件'].tolist())
                if st.button("手動確認報到", key="manual_checkin_btn"):
                    res_status = checkin_user(target_email)
                    if res_status == "Success":
                        st.success("手動報到成功！")
                        st.cache_data.clear()
                        st.rerun()
            else:
                st.error("缺少『電子郵件』欄位，無法執行報到。")
        else:
            st.warning("查無相關資料。")

# -- Tab 3: 完整清單 --
with tab3:
    st.subheader("📋 完整名單預覽")
    if not df_all.empty:
        # 動態顯示現有欄位，避免 KeyError
        desired_cols = ['姓名', '單位', '報到狀態', '連絡電話', '職稱']
        available_cols = [col for col in desired_cols if col in df_all.columns]
        
        if available_cols:
            st.dataframe(df_all[available_cols], use_container_width=True)
        else:
            st.dataframe(df_all, use_container_width=True) # 保底顯示所有資料
    else:
        st.write("目前無資料。")