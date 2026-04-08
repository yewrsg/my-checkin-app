import streamlit as st
import requests
import pandas as pd
import cv2
import numpy as np

# 這裡建議使用 Secrets 存網址，但我們先直接寫入測試
GAS_URL = st.secrets["GAS_URL"]

st.set_page_config(page_title="研習報到站", layout="centered")

def fetch_data():
    return pd.DataFrame(requests.get(GAS_URL).json())

def checkin_user(email):
    return requests.post(GAS_URL, json={"email": email}).text == "Success"

st.title("📲 研習自動報到系統")

tab1, tab2 = st.tabs(["📷 掃描報到", "🔍 手動搜尋"])

with tab1:
    img = st.camera_input("請對準 QR Code")
    if img:
        bytes_data = img.getvalue()
        cv_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
        detector = cv2.QRCodeDetector()
        email, _, _ = detector.detectAndDecode(cv_img)
        
        if email:
            df = fetch_data()
            user = df[df['電子郵件'] == email]
            if not user.empty:
                st.success(f"找到參加者：{user.iloc[0]['姓名']}")
                if st.button("確認報到"):
                    if checkin_user(email):
                        st.balloons()
                        st.success("報到成功！")
            else:
                st.error("查無此資料")

with tab2:
    search = st.text_input("請輸入姓名搜尋")
    if search:
        df = fetch_data()
        if not df.empty:
            # 優化搜尋：確保「姓名」欄位存在才搜尋，並忽略大小寫
            if '姓名' in df.columns:
                res = df[df['姓名'].astype(str).str.contains(search, na=False)]
                
                if not res.empty:
                    # 修改點：自動過濾掉不必要的欄位，只顯示存在的關鍵欄位，避免 KeyError
                    display_cols = [col for col in ['姓名', '單位', '報到狀態'] if col in res.columns]
                    st.write(res[display_cols])
                    
                    # 下拉選單：確保「電子郵件」欄位存在
                    if '電子郵件' in res.columns:
                        target = st.selectbox("選擇人員完成報到", res['電子郵件'].tolist())
                        if st.button("手動確認報到"):
                            if checkin_user(target):
                                st.success(f"{target} 報到成功！")
                    else:
                        st.error("試算表中缺少『電子郵件』欄位，無法執行報到。")
                else:
                    st.warning("查無此姓名。")
            else:
                st.error("試算表標題列找不到『姓名』欄位，請檢查試算表。")
        else:
            st.info("目前資料庫中沒有任何報名資料。")