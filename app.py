import streamlit as st
import requests
import pandas as pd
from streamlit_js_eval import streamlit_js_eval

# --- 1. 基礎設定與 GAS 串接 ---
GAS_URL = st.secrets["GAS_URL"]
st.set_page_config(page_title="研習行動報到站", page_icon="📝", layout="centered")

# --- 2. 資料讀取 (強制轉為字串並處理異常值) ---
@st.cache_data(ttl=10) # 縮短快取時間到 10 秒
def fetch_data():
    try:
        response = requests.get(GAS_URL)
        if response.status_code == 200:
            df = pd.DataFrame(response.json()).astype(str)
            # 解決 Arrow 錯誤與清除空值字串
            df = df.replace(["nan", "None", "undefined", "NaN"], "")
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"資料讀取失敗: {e}")
        return pd.DataFrame()

# --- 3. 報到執行邏輯 ---
def execute_checkin(target_id, name):
    with st.spinner(f'正在為 {name} 辦理報到...'):
        try:
            response = requests.post(GAS_URL, json={"id": target_id})
            if response.text == "Success":
                st.balloons()
                st.success(f"🎊 {name} 報到成功！")
                st.cache_data.clear() # 清除快取以抓取最新狀態
                return True
            elif response.text == "Already Checked In":
                st.warning(f"⚠️ {name} 先前已經完成報到了。")
                return False
            else:
                st.error(f"報到失敗：{response.text}")
                return False
        except Exception as e:
            st.error(f"連線錯誤: {e}")
            return False

# --- 4. 主介面 ---
df_all = fetch_data()

st.title("📲 研習行動報到站")

if not df_all.empty:
    total = len(df_all)
    # 動態檢查欄位名稱
    status_col = next((c for c in ['報到狀態', '狀態'] if c in df_all.columns), None)
    if status_col:
        checked = len(df_all[df_all[status_col].str.contains("已報到", na=False)])
        st.progress(checked / total)
        st.caption(f"📊 目前報到率：{checked} / {total} ({(checked/total)*100:.1f}%)")

st.divider()

tab1, tab2, tab3 = st.tabs(["📷 自動掃描", "🔍 手動報到", "📋 名單總覽"])

# -- Tab 1: 自動掃描 (免拍照) --
with tab1:
    st.subheader("請將 QR Code 對準鏡頭")
    
    # 使用 HTML5-QRCode 嵌入，並透過 JS 直接將結果寫回 Streamlit 的 Session State
    qr_html = """
    <div id="reader" style="width:100%; border-radius: 10px; overflow: hidden;"></div>
    <script src="https://unpkg.com/html5-qrcode"></script>
    <script>
        function onScanSuccess(decodedText) {
            // 將掃描結果發送給父視窗 (Streamlit)
            window.parent.postMessage({
                type: 'streamlit:setComponentValue',
                value: decodedText
            }, '*');
            // 掃描成功後震動提示 (若手機支援)
            if (navigator.vibrate) navigator.vibrate(200);
        }
        let html5QrcodeScanner = new Html5QrcodeScanner("reader", { fps: 15, qrbox: 250 });
        html5QrcodeScanner.render(onScanSuccess);
    </script>
    """
    
    # 這裡我們用一個簡單的文字框當作「接收器」
    # 在某些環境下，JS 注入可能需要手動觸發一次
    scanned_id = st.text_input("掃描到的 ID (自動偵測)", key="qr_receiver", placeholder="等待掃描中...")
    
    components_height = 450
    st.components.v1.html(qr_html, height=components_height)

    if scanned_id:
        # 比對 ID
        id_col = next((c for c in ['隨機ID', 'ID'] if c in df_all.columns), None)
        name_col = next((c for c in ['姓名', 'Name'] if c in df_all.columns), None)
        
        if id_col and name_col:
            user_match = df_all[df_all[id_col] == scanned_id]
            if not user_match.empty:
                user_data = user_match.iloc[0]
                st.info(f"📍 辨識對象：{user_data[name_col]} ({user_data.get('單位', '')})")
                
                # 自動報到按鈕
                if st.button(f"確認【{user_data[name_col]}】報到", type="primary", key="btn_scan"):
                    if execute_checkin(scanned_id, user_data[name_col]):
                        st.rerun()
            else:
                st.error("此 QR Code 不在報名名單內")

# -- Tab 2: 手動報到 --
with tab2:
    st.subheader("🔍 手動搜尋並報到")
    search_query = st.text_input("輸入關鍵字 (姓名、電話或單位)")
    
    if search_query:
        # 過濾包含關鍵字的資料
        mask = df_all.apply(lambda row: row.astype(str).str.contains(search_query, case=False).any(), axis=1)
        search_results = df_all[mask]
        
        if not search_results.empty:
            # 顯示簡化的搜尋清單
            display_cols = [c for c in ['姓名', '單位', '報到狀態', '隨機ID'] if c in search_results.columns]
            st.write(f"找到 {len(search_results)} 筆相關資料：")
            st.table(search_results[display_cols])
            
            # 選擇對象執行報到
            # 使用下拉選單確保選到正確的人
            options = search_results.apply(lambda r: f"{r['姓名']} - {r.get('單位', '')} ({r['隨機ID']})", axis=1).tolist()
            selected_option = st.selectbox("請選擇要辦理報到的對象", options)
            
            if st.button("執行手動報到", type="primary"):
                # 從選項字串中解析出隨機 ID
                selected_rid = selected_option.split('(')[-1].replace(')', '')
                selected_name = selected_option.split(' - ')[0]
                if execute_checkin(selected_rid, selected_name):
                    st.rerun()
        else:
            st.warning("查無此人，請檢查輸入內容。")

# -- Tab 3: 名單總覽 --
with tab3:
    st.subheader("📋 完整名單")
    if not df_all.empty:
        st.dataframe(df_all, width="stretch")
    if st.button("🔄 重新整理資料"):
        st.cache_data.clear()
        st.rerun()