import streamlit as st
import requests
import pandas as pd
from streamlit_qr_scanner import qr_scanner

# --- 基礎設定 ---
GAS_URL = st.secrets["GAS_URL"]

st.set_page_config(page_title="研習行動報到站", page_icon="📝", layout="centered")

# --- 資料讀取與「健檢」函式 ---
@st.cache_data(ttl=15)
def fetch_data():
    try:
        response = requests.get(GAS_URL)
        if response.status_code == 200:
            raw_df = pd.DataFrame(response.json())
            
            # --- 重點修正 1: 解決 ArrowTypeError (連絡電話轉型) ---
            # 將所有資料強制轉為字串 (string)，避免數字與字串混合導致當機
            df = raw_df.astype(str)
            
            # 處理可能出現的 "nan" 或 "None" 字串，讓介面乾淨一點
            df = df.replace(["nan", "None", "undefined"], "")
            return df
        return pd.DataFrame()
    except:
        return pd.DataFrame()

# --- 執行報到 ---
def checkin_user(rid):
    with st.spinner('同步中...'):
        try:
            response = requests.post(GAS_URL, json={"id": rid})
            return response.text
        except Exception as e:
            return f"Error: {e}"

# --- UI 介面 ---
df_all = fetch_data()

st.title("📲 研習行動報到站")

# 顯示進度條 (加入欄位存在檢查)
if not df_all.empty:
    total = len(df_all)
    status_col = '報到狀態' if '報到狀態' in df_all.columns else None
    
    if status_col:
        # 計算已報到人數
        checked = len(df_all[df_all[status_col].str.contains("已報到", na=False)])
        percent = int((checked / total) * 100) if total > 0 else 0
        st.progress(checked / total if total > 0 else 0)
        st.caption(f"📊 目前進度：{checked} / {total} 人 (已完成 {percent}%)")

st.divider()

tab1, tab2, tab3 = st.tabs(["📷 自動掃描", "🔍 手動搜尋", "📋 名單預覽"])

# -- Tab 1: 即時自動掃描 --
with tab1:
    st.subheader("請將 QR Code 對準鏡頭")
    scanned_id = qr_scanner(key="qr_scanner")
    
    if scanned_id:
        st.info(f"掃描結果：{scanned_id}")
        id_col = '隨機ID' if '隨機ID' in df_all.columns else None
        
        if id_col:
            user = df_all[df_all[id_col] == scanned_id]
            if not user.empty:
                name_val = user.iloc[0]['姓名'] if '姓名' in df_all.columns else "未知姓名"
                st.success(f"📍 找到對象：{name_val}")
                
                # 檢查是否已報到
                is_checked = "已報到" in str(user.iloc[0].get('報到狀態', ""))
                if is_checked:
                    st.warning("⚠️ 提醒：此人員已完成報到。")
                else:
                    if st.button(f"確認【{name_val}】報到", type="primary"):
                        res = checkin_user(scanned_id)
                        if res == "Success":
                            st.balloons()
                            st.cache_data.clear()
                            st.rerun()
            else:
                st.error(f"資料庫查無此 ID：{scanned_id}")

# -- Tab 2: 手動搜尋 --
with tab2:
    search = st.text_input("輸入關鍵字搜尋 (姓名/單位/電話)")
    if search and not df_all.empty:
        res = df_all[df_all.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)]
        if not res.empty:
            # --- 重點修正 2: 解決 KeyError (動態選擇欄位) ---
            # 只顯示「真的存在」的欄位，避免因為找不到「單位」而當機
            cols_to_show = [c for c in ['姓名', '單位', '服務單位', '報到狀態', '隨機ID'] if c in res.columns]
            st.dataframe(res[cols_to_show], width="stretch") # 修正過時語法
            
            rid_col = '隨機ID' if '隨機ID' in res.columns else None
            if rid_col:
                target_id = st.selectbox("請選擇報到對象", res[rid_col].tolist())
                if st.button("手動確認報到", key="manual_btn"):
                    res_status = checkin_user(target_id)
                    if res_status == "Success":
                        st.success("手動報到成功！")
                        st.cache_data.clear()
                        st.rerun()
        else:
            st.warning("查無相關資料。")

# -- Tab 3: 名單預覽 --
with tab3:
    st.subheader("📋 完整名單預覽")
    if not df_all.empty:
        # 動態顯示現有欄位，徹底解決 KeyError
        # 如果找不到「單位」，改找「服務單位」或直接顯示全部
        desired = ['姓名', '單位', '服務單位', '職稱', '報到狀態', '隨機ID']
        available = [col for col in desired if col in df_all.columns]
        
        if available:
            st.dataframe(df_all[available], width="stretch")
        else:
            st.dataframe(df_all, width="stretch") # 保底：顯示所有抓到的欄位