import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime
from config import CONN, PN_TO_MODULE

# 数据库连接
conn = sqlite3.connect(CONN)
if 'username' not in st.session_state or not st.session_state.username:
    st.warning("请先登录系统")
    st.stop()
    
# 获取产品和工站列表
with sqlite3.connect(CONN) as conn:
    products = pd.read_sql("SELECT id, pn, module_name FROM Products", conn)
    stations = pd.read_sql("SELECT id, name FROM Stations", conn)

# 创建查询界面
st.subheader("通过ID查询和修改良率数据")

# 输入ID查询
record_id = st.number_input("输入记录ID", min_value=1, step=1)

if st.button("查询记录"):
    # 查询记录
    query = """
    SELECT y.*, p.pn, p.module_name, s.name as station_name
    FROM yielddata y
    LEFT JOIN Products p ON y.product_id = p.id
    LEFT JOIN Stations s ON y.station_id = s.id
    WHERE y.id = ?
    """
    record = pd.read_sql(query, conn, params=(record_id,))
    
    if not record.empty:
        st.session_state.current_record = record.iloc[0].to_dict()
        st.success("记录查询成功!")
    else:
        st.warning("未找到指定ID的记录")

# 显示和编辑记录
if 'current_record' in st.session_state:
    record = st.session_state.current_record
    
    with st.form("edit_yield_form"):
        # 产品选择
        product_options = [f"{p['pn']} - {p['module_name']}" for _, p in products.iterrows()]
        current_product = f"{record['pn']} - {record['module_name']}"
        product_choice = st.selectbox("选择产品*", product_options, 
                                   index=product_options.index(current_product) if current_product in product_options else 0)
        
        # 工站选择
        station_options = [s['name'] for _, s in stations.iterrows()]
        station_choice = st.selectbox("选择工站*", station_options, 
                                     index=station_options.index(record['station_name']) if record['station_name'] in station_options else 0)
        
        # 其他字段
        date_code = st.text_input("日期代码", value=record['date_code'])
        good_count = st.number_input("生产数量", value=record['good_count'], min_value=0)
        bad_count = st.number_input("不良数量", value=record['bad_count'], min_value=0)
        defect_description = st.text_area("不良内容描述", value=record['defect_description'])
        improvement_measures = st.text_area("改善措施", value=record['improvement_measures'])
        
        # 图片和附件上传
        col1, col2 = st.columns(2)
        with col1:
            new_picture = st.file_uploader("更新图片", type=["jpg", "png", "jpeg"], 
                                         help="当前图片: " + record['picture'] if record['picture'] else "无图片")
        with col2:
            new_attachment = st.file_uploader("更新附件", type=["pdf", "doc", "docx", "xlsx"], 
                                           help="当前附件: " + record['attachment'] if record['attachment'] else "无附件")
        
        # 提交修改
        if st.form_submit_button("保存修改"):
            # 处理文件上传
            picture_path = record['picture']
            if new_picture:
                os.makedirs("uploads/productionyield", exist_ok=True)
                picture_path = f"uploads/productionyield/{record_id}_{new_picture.name}"
                with open(picture_path, "wb") as f:
                    f.write(new_picture.getbuffer())
            
            attachment_path = record['attachment']
            if new_attachment:
                os.makedirs("uploads/productionyield", exist_ok=True)
                attachment_path = f"uploads/productionyield/{record_id}_{new_attachment.name}"
                with open(attachment_path, "wb") as f:
                    f.write(new_attachment.getbuffer())
            
            # 获取产品和工站ID
            product_pn = product_choice.split(" - ")[0]
            station_name = station_choice
            
            with sqlite3.connect(CONN) as conn:
                conn.execute("""
                UPDATE YieldData SET
                    product_id = (SELECT id FROM Products WHERE pn = ?),
                    station_id = (SELECT id FROM Stations WHERE name = ?),
                    date_code = ?,
                    good_count = ?,
                    bad_count = ?,
                    defect_description = ?,
                    improvement_measures = ?,
                    picture = ?,
                    attachment = ?
                WHERE id = ?
                """, (
                    product_pn, station_name,
                    date_code, good_count, bad_count,
                    defect_description, improvement_measures,
                    picture_path, attachment_path,
                    record_id
                ))
                conn.commit()
            st.success("记录已更新!")
            st.rerun()
