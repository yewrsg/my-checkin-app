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
        # 每次搜尋都重新抓取最新資料，確保狀態正確
        df = fetch_data()
        if not df.empty:
            if '姓名' in df.columns:
                # 搜尋包含關鍵字的姓名
                res = df[df['姓名'].astype(str).str.contains(search, na=False)]
                
                if not res.empty:
                    # 強制顯示這四個欄位，讓管理員一眼看出狀態
                    cols_to_show = ['姓名', '單位', '連絡電話', '報到狀態']
                    display_cols = [c for c in cols_to_show if c in res.columns]
                    st.dataframe(res[display_cols], use_container_width=True)
                    
                    # 選擇要報到的人員
                    options = res['電子郵件'].tolist()
                    target = st.selectbox("選擇人員執行手動報到", options)
                    
                    # 取得該員目前狀態
                    current_status = res[res['電子郵件'] == target]['報到狀態'].values[0]
                    
                    if current_status == "✅ 已報到":
                        st.warning(f"⚠️ {target} 已經完成報到，無需重複操作。")
                    else:
                        if st.button("確認手動報到"):
                            result = requests.post(GAS_URL, json={"email": target}).text
                            if result == "Success":
                                st.success(f"✅ {target} 手動報到成功！")
                                st.balloons()
                                # 報到成功後建議使用者重新輸入或刷新以更新表格
                            elif result == "Already Checked In":
                                st.warning("該員剛才已由他人完成報到。")
                            else:
                                st.error("報到失敗，請檢查網路或試算表設定。")
                else:
                    st.warning("查無此姓名，請檢查字是否有誤。")
            else:
                st.error("試算表格式錯誤：找不到『姓名』欄位。")