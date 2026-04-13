import streamlit as st
import requests
import pandas as pd
from streamlit_camera_qr_code_scanner import camera_qr_code_scanner

# --- 1. 基礎設定 ---
GAS_URL = st.secrets["GAS_URL"]
st.set_page_config(page_title="研習行動報到站", page_icon="📝", layout="centered")

# --- 2. 資料讀取 (強化轉型與防錯) ---
@st.cache_data(ttl=10)
def fetch_data():
    try:
        response = requests.get(GAS_URL)
        if response.status_code == 200:
            # 讀取資料並將所有欄位轉為字串，避免數字（如電話）造成顯示錯誤
            df = pd.DataFrame(response.json()).astype(str)
            return df.replace(["nan", "None", "undefined"], "")
        return pd.DataFrame()
    except:
        return pd.DataFrame()

# --- 3. 報到執行函式 ---
def run_checkin(rid, name):
    if not rid: return
    with st.spinner(f"正在辦理 {name} 報到..."):
        try:
            res = requests.post(GAS_URL, json={"id": rid})
            if res.text == "Success":
                st.balloons()
                st.success(f"✅ {name} 報到成功！")
                st.cache_data.clear() # 強制更新資料
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
    status_col = '報到狀態' if '報到狀態' in df_all.columns else None
    if status_col:
        checked = len(df_all[df_all[status_col].str.contains("已報到", na=False)])
        st.caption(f"📊 目前進度：{checked} / {len(df_all)}")
        st.progress(checked / len(df_all))

st.divider()

tab1, tab2, tab3 = st.tabs(["📷 自動掃描報到", "🔍 手動搜尋報到", "📋 名單預覽"])

# -- Tab 1: 自動掃描 --
with tab1:
    st.subheader("請將 QR Code 對準鏡頭")
    # 使用專用元件，掃描後會直接將結果賦值給變數，不必拍照
    scanned_id = camera_qr_code_scanner(key='my_scanner')
    
    if scanned_id:
        st.info(f"掃描成功！ID: {scanned_id}")
        # 比對 ID
        id_col = '隨機ID' if '隨機ID' in df_all.columns else None
        if id_col:
            user = df_all[df_all[id_col] == scanned_id]
            if not user.empty:
                name_val = user.iloc[0]['姓名']
                st.write(f"📍 找到對象：**{name_val}**")
                if st.button(f"確認【{name_val}】報到", type="primary"):
                    if run_checkin(scanned_id, name_val):
                        st.rerun()
            else:
                st.error("此 QR Code 不在名單中。")

# -- Tab 2: 手動報到 (優化流程) --
with tab2:
    st.subheader("🔍 手動輸入資料報到")
    search_keyword = st.text_input("請輸入姓名、電話或單位關鍵字", placeholder="例如：游榮祥")
    
    if search_keyword:
        # 過濾包含關鍵字的資料
        mask = df_all.apply(lambda row: row.astype(str).str.contains(search_keyword, case=False).any(), axis=1)
        search_results = df_all[mask]
        
        if not search_results.empty:
            st.write(f"找到 {len(search_results)} 筆相符資料：")
            
            # 將搜尋結果整理成易讀的格式供下拉選單選擇
            options = []
            id_map = {}
            for _, row in search_results.iterrows():
                label = f"{row['姓名']} | {row.get('單位','')} | {row.get('報到狀態','')}"
                options.append(label)
                id_map[label] = (row['隨機ID'], row['姓名'])
            
            selected = st.selectbox("請點擊下方選擇正確的人員：", options)
            
            if st.button("點我執行手動報到", type="primary"):
                target_rid, target_name = id_map[selected]
                if run_checkin(target_rid, target_name):
                    st.rerun()
        else:
            st.warning("查無相關資料，請檢查輸入。")

# -- Tab 3: 名單預覽 --
with tab3:
    if not df_all.empty:
        st.dataframe(df_all[['姓名', '單位', '報到狀態', '隨機ID']], width="stretch")
    if st.button("🔄 重新整理資料"):
        st.cache_data.clear()
        st.rerun()