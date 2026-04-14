import streamlit as st
import requests
import pandas as pd
import cv2
import numpy as np

# --- 1. 基礎設定 ---
GAS_URL = st.secrets.get("GAS_URL", "")

# --- 2. 掃描解碼邏輯 ---
def decode_qr(image):
    # 將上傳的照片轉換為 OpenCV 格式
    file_bytes = np.asarray(bytearray(image.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    
    # 初始化 QR Code 偵測器
    detector = cv2.QRCodeDetector()
    data, bbox, _ = detector.detectAndDecode(img)
    return data

# --- 3. UI 介面 ---
st.title("📲 研習行動報到站 (原生版)")
df_all = fetch_data() # 您原本抓取名單的函式

tab1, tab2, tab3 = st.tabs(["📷 拍照報到", "🔍 手動報到", "📋 名單預覽"])

with tab1:
    st.subheader("使用相機拍照報到")
    
    # 使用 Streamlit 原生相機元件
    img_file = st.camera_input("請將 QR Code 對準鏡頭並拍照")

    if img_file:
        with st.spinner("正在辨識 QR Code..."):
            qr_data = decode_qr(img_file)
            
            if qr_data:
                st.success(f"辨識成功：ID {qr_data}")
                # 呼叫原本的 GAS 報到 API
                res = requests.post(GAS_URL, json={"id": qr_data})
                if res.text == "Success":
                    st.balloons()
                    st.success("✅ 報到完成！")
                else:
                    st.error(f"報到失敗：{res.text}")
            else:
                st.warning("無法辨識 QR Code，請靠近一點重新拍攝。")

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