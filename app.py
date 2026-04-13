import streamlit as st
import requests
import pandas as pd
from streamlit_camera_qr_code_scanner import camera_qr_code_scanner

# --- 1. 基礎設定 ---
GAS_URL = st.secrets["GAS_URL"]
st.set_page_config(page_title="研習行動報到站", page_icon="📝", layout="centered")

# --- 2. 資料讀取 (強化防錯與自動修正類型) ---
@st.cache_data(ttl=10)
def fetch_data():
    try:
        response = requests.get(GAS_URL)
        if response.status_code == 200:
            # 讀取資料
            data = response.json()
            df = pd.DataFrame(data)
            # 【修正重點 1】強制將所有資料轉為字串，徹底解決 ArrowTypeError (如連絡電話是數字的問題)
            df = df.astype(str)
            # 清理常見的空值字串
            df = df.replace(["nan", "None", "undefined", "<NA>"], "")
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"資料讀取失敗：{e}")
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
                st.cache_data.clear() # 報到後強制重新抓取資料
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

# 檢查必要欄位是否存在，避免 KeyError
cols = df_all.columns.tolist()
id_col = '隨機ID' if '隨機ID' in cols else None
name_col = '姓名' if '姓名' in cols else None
status_col = '報到狀態' if '報到狀態' in cols else None

if not df_all.empty and status_col:
    checked = len(df_all[df_all[status_col].str.contains("已報到", na=False)])
    st.caption(f"📊 目前進度：{checked} / {len(df_all)}")
    st.progress(checked / len(df_all))

st.divider()

tab1, tab2, tab3 = st.tabs(["📷 自動掃描", "🔍 手動搜尋", "📋 完整名單"])

# -- Tab 1: 自動掃描 --
with tab1:
    st.subheader("請將 QR Code 對準鏡頭")
    scanned_id = camera_qr_code_scanner(key='my_scanner')
    
    if scanned_id:
        st.info(f"掃描結果：{scanned_id}")
        if id_col and name_col:
            user = df_all[df_all[id_col] == scanned_id]
            if not user.empty:
                name_val = user.iloc[0][name_col]
                st.write(f"📍 找到對象：**{name_val}**")
                if st.button(f"確認【{name_val}】報到", type="primary", key="qr_btn"):
                    if run_checkin(scanned_id, name_val):
                        st.rerun()
            else:
                st.error("此 QR Code 不在名單中，請檢查或改用手動搜尋。")

# -- Tab 2: 手動搜尋 --
with tab2:
    st.subheader("🔍 手動輸入資料")
    search_keyword = st.text_input("請輸入姓名或關鍵字", placeholder="例如：姓名")
    
    if search_keyword and not df_all.empty:
        # 全域搜尋
        mask = df_all.apply(lambda row: row.astype(str).str.contains(search_keyword, case=False).any(), axis=1)
        search_results = df_all[mask]
        
        if not search_results.empty:
            options = []
            id_map = {}
            for _, row in search_results.iterrows():
                # 動態判斷要顯示哪些資訊在選單中
                info = f"{row.get('姓名', '未知')} | {row.get('單位', '無單位')} | {row.get('報到狀態', '')}"
                options.append(info)
                id_map[info] = (row.get('隨機ID'), row.get('姓名'))
            
            selected = st.selectbox("請選擇正確的人員：", options)
            if st.button("確認手動報到", type="primary", key="manual_btn"):
                target_rid, target_name = id_map[selected]
                if run_checkin(target_rid, target_name):
                    st.rerun()
        else:
            st.warning("查無相關資料。")

# -- Tab 3: 名單預覽 --
with tab3:
    st.subheader("名單預覽")
    if not df_all.empty:
        # 【修正重點 2】動態過濾要顯示的欄位，如果該欄位不存在則忽略，避免 KeyError
        display_cols = [c for c in ['姓名', '單位', '報到狀態', '隨機ID'] if c in df_all.columns]
        # 【修正重點 3】使用 width="stretch" 取代舊版的 use_container_width
        st.dataframe(df_all[display_cols], width="stretch")
    
    if st.button("🔄 重新整理資料"):
        st.cache_data.clear()
        st.rerun()