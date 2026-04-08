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
        res = df[df['姓名'].str.contains(search, na=False)]
        st.write(res[['姓名', '單位', '報到狀態']])
        if not res.empty:
            target = st.selectbox("選擇人員", res['電子郵件'].tolist())
            if st.button("手動報到"):
                if checkin_user(target):
                    st.success("報到成功！")