import streamlit as st
import requests
import pandas as pd
from streamlit_camera_qr_code_scanner import camera_qr_code_scanner

# --- 1. 基礎設定 ---
# 請確保 secrets 中已設定 GAS_URL
GAS_URL = st.secrets.get("GAS_URL", "")
st.set_page_config(page_title="研習行動報到站", page_icon="📝", layout="centered")

# --- 2. 資料讀取 (強化類型轉換，解決 ArrowTypeError) ---
@st.cache_data(ttl=10)
def fetch_data():
    if not GAS_URL:
        st.error("請在 Secrets 中設定 GAS_URL")
        return pd.DataFrame()
    try:
        response = requests.get(GAS_URL)
        if response.status_code == 200:
            data = response.json()
            df = pd.DataFrame(data)
            
            # 【關鍵修正】強制將所有欄位轉換為字串，並處理空值
            # 這樣可以徹底解決「連絡電話」導致的 ArrowTypeError
            for col in df.columns:
                df[col] = df[col].apply(lambda x: str(x) if pd.notnull(x) and x != "" else "")
            
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
                st.cache_data.clear() # 成功後清除快取
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

# 檢查資料並顯示進度
if not df_all.empty:
    # 動態判斷欄位名稱，增加相容性
    id_col = next((c for c in ['隨機ID', 'ID'] if c in df_all.columns), None)
    name_col = next((c for c in ['姓名', 'Name'] if c in df_all.columns), None)
    status_col = next((c for c in ['報到狀態', '狀態'] if c in df_all.columns), None)

    if status_col:
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
                    st.error("此 ID 不在名單中，請檢查或改用手動搜尋。")

    # -- Tab 2: 手動搜尋 --
    with tab2:
        st.subheader("🔍 手動輸入資料")
        search_keyword = st.text_input("請輸入姓名或關鍵字", placeholder="例如：姓名")
        
        if search_keyword:
            mask = df_all.apply(lambda row: row.str.contains(search_keyword, case=False).any(), axis=1)
            search_results = df_all[mask]
            
            if not search_results.empty:
                options = []
                id_map = {}
                for _, row in search_results.iterrows():
                    # 安全獲取顯示資訊
                    u_name = row.get(name_col, "未知")
                    u_unit = row.get('單位', '無單位')
                    u_status = row.get(status_col, '')
                    label = f"{u_name} | {u_unit} | {u_status}"
                    options.append(label)
                    id_map[label] = (row.get(id_col), u_name)
                
                selected = st.selectbox("請選擇人員：", options)
                if st.button("確認報到", type="primary", key="manual_btn"):
                    target_rid, target_name = id_map[selected]
                    if run_checkin(target_rid, target_name):
                        st.rerun()
            else:
                st.warning("查無相關資料。")

    # -- Tab 3: 名單預覽 --
    with tab3:
        st.subheader("名單預覽")
        # 【關鍵修正】動態過濾要顯示的欄位，如果試算表沒「單位」也不會報錯
        display_cols = [c for c in ['姓名', '單位', '報到狀態', '隨機ID'] if c in df_all.columns]
        # 使用新的參數 width="stretch" 
        st.dataframe(df_all[display_cols], width="stretch")
        
        if st.button("🔄 重新整理資料"):
            st.cache_data.clear()
            st.rerun()
else:
    st.warning("目前無法獲取資料，請檢查 GAS 連結或試算表權限。")