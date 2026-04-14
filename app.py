import streamlit as st
import requests
import pandas as pd
import cv2
import numpy as np

# --- 1. 基礎設定 ---
GAS_URL = st.secrets.get("GAS_URL", "")
st.set_page_config(page_title="研習報到系統", page_icon="📝")

# --- 2. 資料獲取 ---
@st.cache_data(ttl=10)
def fetch_data():
    if not GAS_URL: return pd.DataFrame()
    try:
        res = requests.get(f"{GAS_URL}?action=getData")
        return pd.DataFrame(res.json()) if res.status_code == 200 else pd.DataFrame()
    except:
        return pd.DataFrame()

# --- 3. QR Code 辨識邏輯 ---
def decode_qr(image_file):
    # 將上傳的照片轉換為 OpenCV 格式
    file_bytes = np.asarray(bytearray(image_file.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    
    # 初始化辨識器
    detector = cv2.QRCodeDetector()
    # 嘗試偵測並解碼
    data, bbox, _ = detector.detectAndDecode(img)
    
    # 如果失敗，嘗試轉灰階增加辨識率
    if not data:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        data, _, _ = detector.detectAndDecode(gray)
    return data

# --- 4. UI 介面 ---
st.title("📲 研習行動報到站")
df_all = fetch_data()

tab1, tab2, tab3 = st.tabs(["📷 拍照報到", "🔍 手動報到", "📋 名單預覽"])

with tab1:
    st.subheader("請對準 QR Code 拍照")
    # 原生相機元件，100% 解決權限問題
    captured_img = st.camera_input("拍照後系統會自動辨識")

    if captured_img:
        with st.spinner("辨識中..."):
            qr_data = decode_qr(captured_img)
            
            if qr_data:
                st.success(f"辨識成功：ID {qr_data}")
                # 送出報到請求到 GAS
                try:
                    res = requests.post(GAS_URL, json={"id": qr_data})
                    if res.text == "Success":
                        st.balloons()
                        st.success("✅ 報到成功！")
                        st.cache_data.clear() # 清除快取以刷新名單
                    else:
                        st.error(f"報到失敗：{res.text}")
                except Exception as e:
                    st.error(f"連線至 GAS 出錯：{e}")
            else:
                st.warning("⚠️ 無法偵測 QR Code。請將鏡頭對準、光線充足並重新拍攝。")

# --- Tab 2 & 3 保留您原本正確的功能 ---
with tab2:
    # ... 您原有的手動報到代碼 ...
    pass

with tab3:
    if not df_all.empty:
        st.dataframe(df_all)