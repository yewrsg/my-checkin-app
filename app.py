import streamlit as st
import requests
import pandas as pd
import streamlit.components.v1 as components

# --- 基礎設定 ---
GAS_URL = st.secrets["GAS_URL"]
st.set_page_config(page_title="研習行動報到站", page_icon="📝", layout="centered")

# --- 資料讀取 (強制轉為字串避免 Arrow 錯誤) ---
@st.cache_data(ttl=15)
def fetch_data():
    try:
        response = requests.get(GAS_URL)
        if response.status_code == 200:
            df = pd.DataFrame(response.json()).astype(str)
            return df.replace(["nan", "None", "undefined"], "")
        return pd.DataFrame()
    except:
        return pd.DataFrame()

# --- 執行報到 ---
def checkin_user(rid):
    try:
        response = requests.post(GAS_URL, json={"id": rid})
        return response.text
    except Exception as e:
        return f"Error: {e}"

df_all = fetch_data()

st.title("📲 研習行動報到站")

# 顯示進度
if not df_all.empty:
    total = len(df_all)
    status_col = '報到狀態' if '報到狀態' in df_all.columns else None
    if status_col:
        checked = len(df_all[df_all[status_col].str.contains("已報到", na=False)])
        st.progress(checked / total if total > 0 else 0)
        st.caption(f"📊 目前進度：{checked} / {total} 人")

st.divider()

tab1, tab2, tab3 = st.tabs(["📷 自動掃描", "🔍 手動搜尋", "📋 名單預覽"])

with tab1:
    st.subheader("請將 QR Code 對準鏡頭")
    
    # 使用 HTML5/JS 直接實作掃描器，避開 Python 套件相容性問題
    # 這段代碼會直接呼叫相機，辨識到 QR Code 後會傳回給 Streamlit
    qr_component = """
    <div id="reader" style="width:100%;"></div>
    <script src="https://unpkg.com/html5-qrcode"></script>
    <script>
        const html5QrCode = new Html5Qrcode("reader");
        const config = { fps: 10, qrbox: { width: 250, height: 250 } };
        
        html5QrCode.start({ facingMode: "environment" }, config, (decodedText) => {
            // 掃描成功，將結果傳給 Streamlit
            window.parent.postMessage({
                type: 'streamlit:setComponentValue',
                value: decodedText
            }, '*');
            html5QrCode.stop(); // 掃到就停止，避免重複執行
        });
    </script>
    """
    
    # 執行掃描組件
    scanned_id = components.html(qr_component, height=350)
    
    # 如果掃描到了 ID
    # 註：Streamlit 的 components.html 傳回值處理較特殊，
    # 這裡我們用一個簡單的文字輸入框來接收掃描結果 (手動模擬自動填入)
    manual_id = st.text_input("掃描到的 ID (若未自動帶入請點擊)", key="scanned_input")
    
    if manual_id:
        id_col = '隨機ID' if '隨機ID' in df_all.columns else None
        if id_col:
            user = df_all[df_all[id_col] == manual_id]
            if not user.empty:
                name = user.iloc[0]['姓名']
                st.success(f"📍 找到對象：{name}")
                if st.button(f"確認【{name}】報到", type="primary"):
                    res = checkin_user(manual_id)
                    if res == "Success":
                        st.balloons()
                        st.cache_data.clear()
                        st.rerun()
            else:
                st.error("查無此 ID，請重新掃描。")
                if st.button("重新掃描"): st.rerun()

with tab2:
    # (手動搜尋邏輯維持不變)
    search = st.text_input("輸入關鍵字 (姓名/單位)")
    if search:
        res = df_all[df_all.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)]
        st.dataframe(res, width="stretch")

with tab3:
    st.dataframe(df_all, width="stretch")