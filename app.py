import streamlit as st
import requests
import pandas as pd
from streamlit_camera_qr_code_scanner import camera_qr_code_scanner

# --- 1. 基礎設定 ---
GAS_URL = st.secrets.get("GAS_URL", "")
st.set_page_config(page_title="研習行動報到站", page_icon="📝", layout="centered")

# --- 2. 資料讀取 (針對 Log 中的 ArrowTypeError 與空值進行修正) ---
@st.cache_data(ttl=10)
def fetch_data():
    if not GAS_URL:
        st.error("❌ 尚未設定 GAS_URL，請檢查 Secrets。")
        return pd.DataFrame()
    try:
        response = requests.get(GAS_URL)
        if response.status_code == 200:
            df = pd.DataFrame(response.json())
            
            # 【對應 Log 修正】清除標題空格，避免 KeyError
            df.columns = df.columns.str.strip()
            
            # 【對應 Log 修正】強制將所有內容轉為字串，徹底解決「連絡電話」導致的 ArrowTypeError
            df = df.astype(str)
            
            # 清理常見空值字串
            df = df.replace(["nan", "None", "undefined", "<NA>"], "")
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"資料讀取失敗：{e}")
        return pd.DataFrame()

# --- 3. 報到執行邏輯 ---
def run_checkin(rid, name):
    if not rid: return
    with st.spinner(f"正在為 {name} 辦理報到..."):
        try:
            res = requests.post(GAS_URL, json={"id": rid})
            if res.text == "Success":
                st.balloons()
                st.success(f"🎊 {name} 報到成功！")
                st.cache_data.clear() # 報到後清除快取以同步資料
                return True
            else:
                st.warning(f"結果：{res.text}")
                return False
        except Exception as e:
            st.error(f"連線失敗：{e}")
            return False

# --- 4. 主介面 ---
df_all = fetch_data()

st.title("📲 研習行動報到站")

if not df_all.empty:
    # 自動偵測關鍵欄位
    cols = df_all.columns.tolist()
    id_col = next((c for c in ['隨機ID', 'ID'] if c in cols), None)
    name_col = next((c for c in ['姓名'] if c in cols), None)
    status_col = next((c for c in ['報到狀態', '狀態'] if c in cols), None)

    if status_col:
        checked = len(df_all[df_all[status_col].str.contains("已報到", na=False)])
        st.caption(f"📊 目前進度：{checked} / {len(df_all)}")
        st.progress(checked / len(df_all))

    st.divider()

    tab1, tab2, tab3 = st.tabs(["📷 自動掃描", "🔍 手動搜尋", "📋 名單預覽"])

    with tab1:
        st.subheader("請將 QR Code 對準鏡頭")
        # 啟動掃描器
        scanned_id = camera_qr_code_scanner(key='my_scanner')
        
        if scanned_id:
            st.info(f"掃描成功：{scanned_id}")
            if id_col and name_col:
                user = df_all[df_all[id_col] == scanned_id]
                if not user.empty:
                    name_val = user.iloc[0][name_col]
                    st.write(f"📍 找到對象：**{name_val}**")
                    if st.button(f"確認【{name_val}】報到", type="primary"):
                        if run_checkin(scanned_id, name_val):
                            st.rerun()
                else:
                    st.error("查無此 ID，請確認名單內容。")

    with tab2:
        st.subheader("🔍 手動輸入資料")
        search_q = st.text_input("輸入關鍵字 (姓名/電話)")
        if search_q:
            mask = df_all.apply(lambda row: row.str.contains(search_q, case=False).any(), axis=1)
            results = df_all[mask]
            
            if not results.empty:
                options = []
                id_map = {}
                for _, row in results.iterrows():
                    # 安全組合顯示內容，避免 KeyError
                    u_name = row.get(name_col, '未知')
                    u_unit = row.get('單位', '---')
                    label = f"{u_name} | {u_unit} | {row.get(status_col, '')}"
                    options.append(label)
                    id_map[label] = (row.get(id_col), u_name)
                
                selected = st.selectbox("請選擇人員：", options)
                if st.button("確認報到", type="primary"):
                    target_rid, target_name = id_map[selected]
                    if run_checkin(target_rid, target_name):
                        st.rerun()
            else:
                st.warning("查無資料。")

    with tab3:
        st.subheader("📋 名單預覽")
        # 【對應 Log 修正】動態過濾欄位，即使沒有「單位」欄位也不會報錯
        display_list = ['姓名', '單位', '報到狀態', '隨機ID']
        actual_display = [c for c in display_list if c in df_all.columns]
        
        # 【對應 Log 修正】使用 width="stretch"
        st.dataframe(df_all[actual_display], width="stretch")
        
        if st.button("🔄 重新整理資料"):
            st.cache_data.clear()
            st.rerun()