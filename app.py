import streamlit as st
import requests
import pandas as pd
from streamlit_camera_qr_code_scanner import camera_qr_code_scanner

# --- 1. 基礎設定 ---
# 請確保 Streamlit Cloud 的 Secrets 中已正確設定 GAS_URL
GAS_URL = st.secrets.get("GAS_URL", "")
st.set_page_config(page_title="研習行動報到站", page_icon="📝", layout="centered")

# --- 2. 資料讀取 (強化防錯與類型轉換) ---
@st.cache_data(ttl=10)
def fetch_data():
    if not GAS_URL:
        st.error("❌ 錯誤：請在 Secrets 中設定 GAS_URL")
        return pd.DataFrame()
    try:
        response = requests.get(GAS_URL)
        if response.status_code == 200:
            data = response.json()
            df = pd.DataFrame(data)
            
            # 【關鍵修正 1】清理欄位標題，移除可能的空格或換行
            df.columns = df.columns.str.strip()
            
            # 【關鍵修正 2】強制將所有欄位轉為字串 (解決 ArrowTypeError 報錯)
            # 這能確保「連絡電話」等數字欄位不會導致系統崩潰
            df = df.astype(str)
            
            # 處理空值字串
            df = df.replace(["nan", "None", "undefined", "<NA>"], "")
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"資料讀取失敗：{e}")
        return pd.DataFrame()

# --- 3. 報到執行函式 ---
def run_checkin(rid, name):
    if not rid: return
    with st.spinner(f"正在為 {name} 辦理報到..."):
        try:
            response = requests.post(GAS_URL, json={"id": rid})
            if response.text == "Success":
                st.balloons()
                st.success(f"🎊 {name} 報到成功！")
                st.cache_data.clear() # 報到後強制更新快取
                return True
            else:
                st.warning(f"結果：{response.text}")
                return False
        except Exception as e:
            st.error(f"連線失敗：{e}")
            return False

# --- 4. 主介面邏輯 ---
df_all = fetch_data()

st.title("📲 研習行動報到站")

# 自動偵測關鍵欄位名稱
if not df_all.empty:
    cols = df_all.columns.tolist()
    id_col = next((c for c in ['隨機ID', 'ID', 'id'] if c in cols), None)
    name_col = next((c for c in ['姓名', 'Name', 'name'] if c in cols), None)
    status_col = next((c for c in ['報到狀態', '狀態', 'status'] if c in cols), None)

    # 顯示整體報到進度
    if status_col:
        checked_count = len(df_all[df_all[status_col].str.contains("已報到", na=False)])
        st.caption(f"📊 目前報到率：{checked_count} / {len(df_all)}")
        st.progress(checked_count / len(df_all))

    st.divider()

    tab1, tab2, tab3 = st.tabs(["📷 自動掃描", "🔍 手動報到", "📋 名單預覽"])

    # -- Tab 1: 自動掃描 --
    with tab1:
        st.subheader("請將 QR Code 對準鏡頭")
        # 掃描器組件
        scanned_id = camera_qr_code_scanner(key='my_scanner')
        
        if scanned_id:
            st.info(f"掃描成功：{scanned_id}")
            if id_col and name_col:
                # 尋找匹配的人員
                user_match = df_all[df_all[id_col] == scanned_id]
                if not user_match.empty:
                    target_name = user_match.iloc[0][name_col]
                    st.write(f"📍 找到對象：**{target_name}**")
                    if st.button(f"確認【{target_name}】報到", type="primary", key="qr_btn"):
                        if run_checkin(scanned_id, target_name):
                            st.rerun()
                else:
                    st.error("查無此 ID，請確認 QR Code 是否正確。")

    # -- Tab 2: 手動搜尋與報到 --
    with tab2:
        st.subheader("🔍 搜尋姓名進行報到")
        search_q = st.text_input("輸入關鍵字 (姓名、電話或單位)")
        
        if search_q:
            # 全欄位關鍵字過濾
            mask = df_all.apply(lambda row: row.str.contains(search_q, case=False).any(), axis=1)
            search_results = df_all[mask]
            
            if not search_results.empty:
                # 建立易讀的選單選項
                options_list = []
                id_map = {}
                for _, row in search_results.iterrows():
                    # 安全地組合顯示文字，若欄位不存在則忽略
                    display_text = f"{row.get(name_col, '未知')} | {row.get('單位', '---')} | {row.get(status_col, '')}"
                    options_list.append(display_text)
                    id_map[display_text] = (row.get(id_col), row.get(name_col))
                
                selected_person = st.selectbox("請選擇正確的人員：", options_list)
                if st.button("執行手動報到", type="primary", key="manual_btn"):
                    target_rid, target_name = id_map[selected_person]
                    if run_checkin(target_rid, target_name):
                        st.rerun()
            else:
                st.warning("查無相關資料。")

    # -- Tab 3: 名單預覽 --
    with tab3:
        st.subheader("📋 完整名單預覽")
        # 【關鍵修正 3】動態選擇顯示欄位，若「單位」不存在則自動過濾，防止 KeyError
        wanted = ['姓名', '單位', '報到狀態', '隨機ID']
        display_cols = [c for c in wanted if c in df_all.columns]
        
        # 【關鍵修正 4】使用新的 width="stretch" 參數
        st.dataframe(df_all[display_cols], width="stretch")
        
        if st.button("🔄 重新整理資料"):
            st.cache_data.clear()
            st.rerun()
else:
    st.warning("目前讀取不到任何資料。請確認您的 Google 試算表權限與 GAS 連結。")