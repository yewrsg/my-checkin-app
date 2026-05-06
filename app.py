import streamlit as st
import requests
import pandas as pd
import cv2
import numpy as np

# --- 1. 基礎設定 ---
GAS_URL = st.secrets.get("GAS_URL", "")
ADMIN_KEY = st.secrets.get("ADMIN_KEY", "")

st.set_page_config(page_title="研習報到系統", page_icon="📝")

# --- 側邊欄：權限管控 ---
with st.sidebar:
    st.header("🔐 管理員驗證")
    input_key = st.text_input("請輸入報到授權碼", type="password")
    is_authorized = (input_key == ADMIN_KEY)
    
    if is_authorized:
        st.success("身分驗證成功")
    elif input_key:
        st.error("授權碼錯誤")
    else:
        st.info("請輸入授權碼以啟用報到功能")

# --- 2. 資料獲取 ---
@st.cache_data(ttl=5) # 縮短快取時間，加速重新讀取
def fetch_data():
    if not GAS_URL: return pd.DataFrame()
    try:
        # 強制加入 action=getData 參數
        res = requests.get(f"{GAS_URL}?action=getData", timeout=15)
        if res.status_code == 200:
            data = res.json()
            return pd.DataFrame(data)
        return pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()

# --- 3. QR Code 辨識 ---
def decode_qr(image_file):
    file_bytes = np.asarray(bytearray(image_file.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    detector = cv2.QRCodeDetector()
    data, _, _ = detector.detectAndDecode(img)
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
    if is_authorized:
        captured_img = st.camera_input("拍照後系統會自動辨識")
        if captured_img:
            with st.spinner("辨識中..."):
                qr_data = decode_qr(captured_img)
                if qr_data:
                    st.info(f"辨識到 ID: {qr_data}")
                    res = requests.post(GAS_URL, json={"id": qr_data, "key": input_key})
                    if res.text == "Success":
                        st.balloons()
                        st.success("✅ 報到成功！")
                        st.cache_data.clear()
                    else:
                        st.error(f"報到失敗：{res.text}")
                else:
                    st.warning("⚠️ 無法偵測 QR Code。")
    else:
        st.warning("🔒 請先於側邊欄輸入授權碼。")

with tab2:
    st.subheader("🔍 搜尋學員並報到")
    if is_authorized:
        search_query = st.text_input("輸入姓名或單位搜尋", placeholder="例如：王小明")
        if not df_all.empty:
            # 確保搜尋時不分大小寫
            mask = df_all.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)
            filtered_df = df_all[mask] if search_query else pd.DataFrame()
            
            if not filtered_df.empty:
                for idx, row in filtered_df.iterrows():
                    col1, col2 = st.columns([3, 1])
                    user_uid = str(row.get("UID", ""))
                    user_name = row.get("姓名", "未知")
                    status = row.get("報到狀態", "")
                    
                    with col1:
                        st.write(f"{'✅' if status == '已報到' else '❌'} **{user_name}** ({row.get('單位', '無')})")
                    with col2:
                        if status != "已報到":
                            if st.button("報到", key=f"btn_{user_uid}_{idx}"):
                                res = requests.post(GAS_URL, json={"id": user_uid, "key": input_key})
                                if res.text == "Success":
                                    st.toast(f"✅ {user_name} 成功！")
                                    st.cache_data.clear()
                                    st.rerun()
                                else:
                                    st.error(res.text)
                    st.divider()
            elif search_query:
                st.write("查無資料。")
        else:
            st.warning("目前名單為空，請確認 GAS 連結或試算表內容。")
    else:
        st.warning("🔒 請先於側邊欄輸入授權碼。")

with tab3:
    st.subheader("📋 目前報到清單")
    if not df_all.empty:
        st.dataframe(df_all, use_container_width=True)
        if st.button("🔄 重新整理"):
            st.cache_data.clear()
            st.rerun()
    else:
        st.info("暫無資料或正在讀取中...")