import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime
from config import CONN

# 数据库连接
conn = sqlite3.connect(CONN)
if 'username' not in st.session_state or not st.session_state.username:
    st.warning("请先登录系统")
    st.stop()

# 确保生产基础数据表存在
def init_production_tables():
    with sqlite3.connect(CONN) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS Stations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            create_date DATE NOT NULL
        )""")
        
        conn.execute("""
        CREATE TABLE IF NOT EXISTS Products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pn TEXT NOT NULL UNIQUE,
            module_name TEXT NOT NULL,
            description TEXT,
            create_date DATE NOT NULL
        )""")
        
        conn.execute("""
        CREATE TABLE IF NOT EXISTS YieldData (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            station_id INTEGER NOT NULL,
            date_code TEXT NOT NULL,
            production_count INTEGER NOT NULL,
            bad_count INTEGER NOT NULL,
            defect_description TEXT,
            improvement_measures TEXT,
            picture TEXT,
            attachment TEXT,
            create_date DATE NOT NULL,
            FOREIGN KEY(product_id) REFERENCES Products(id),
            FOREIGN KEY(station_id) REFERENCES Stations(id)
        )""")

# 初始化表
init_production_tables()

# 主界面
st.subheader("Add Station and Product")


# 创建station和product放在同一行
col1, col2 = st.columns(2)
with col1:
    with st.expander("添加工作站"):
        with st.form("station_form"):
            name = st.text_input("工作站名称*")
            description = st.text_area("描述")
            
            submitted = st.form_submit_button("提交")
            if submitted:
                if not name:
                    st.error("请填写工作站名称")
                else:
                    with sqlite3.connect(CONN) as conn:
                        try:
                            conn.execute("""
                            INSERT INTO Stations (name, description, create_date)
                            VALUES (?, ?, ?)
                            """, (name, description, datetime.now().date()))
                            conn.commit()
                            st.success("工作站添加成功!")
                        except sqlite3.IntegrityError:
                            st.error("该工作站名称已存在")

with col2:
    with st.expander("添加产品"):
        with st.form("product_form"):
            pn = st.text_input("产品编号(PN)*")
            module_name = st.text_input("模块名称Module Name*")
            description = st.text_area("产品描述")
            
            submitted = st.form_submit_button("提交")
            if submitted:
                if not all([pn, module_name]):
                    st.error("请填写所有必填字段(*)")
                else:
                    with sqlite3.connect(CONN) as conn:
                        try:
                            conn.execute("""
                            INSERT INTO Products (pn, module_name, description, create_date)
                            VALUES (?, ?, ?, ?)
                            """, (pn, module_name, description, datetime.now().date()))
                            conn.commit()
                            st.success("产品添加成功!")
                        except sqlite3.IntegrityError:
                            st.error("该产品编号已存在")

# 显示现有数据
st.write("---")
st.subheader("现有基础数据")

# 使用tabs替代expand实现并列显示
tab1, tab2 = st.tabs(["工作站列表", "产品列表"])

with tab1:
    with sqlite3.connect(CONN) as conn:
        stations = pd.read_sql("SELECT id, name, description FROM Stations", conn)
    if not stations.empty:
        for _, station in stations.iterrows():
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"**{station['name']}**")
                if station['description']:
                    st.caption(station['description'])
            with col2:
                with st.popover("操作"):
                    with st.form(f"edit_station_{station['id']}"):
                        new_name = st.text_input("工作站名称", value=station['name'])
                        new_desc = st.text_area("描述", value=station['description'])
                        
                        if st.form_submit_button("更新"):
                            with sqlite3.connect(CONN) as conn:
                                conn.execute("""
                                UPDATE Stations SET name=?, description=? WHERE id=?
                                """, (new_name, new_desc, station['id']))
                                conn.commit()
                            st.success("工作站已更新!")
                            st.rerun()
                        if st.form_submit_button("删除", type="secondary"):
                            with sqlite3.connect(CONN) as conn:
                                conn.execute("DELETE FROM Stations WHERE id=?", (station['id'],))
                                conn.commit()
                            st.success("工作站已删除!")
                            st.rerun()
    else:
        st.warning("暂无工作站数据")

with tab2:
    with sqlite3.connect(CONN) as conn:
        products = pd.read_sql("SELECT id, pn, module_name, description FROM Products", conn)
    if not products.empty:
        for _, product in products.iterrows():
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"**{product['pn']}** - {product['module_name']}")
                if product['description']:
                    st.caption(product['description'])
            with col2:
                with st.popover("操作"):
                    with st.form(f"edit_product_{product['id']}"):
                        new_pn = st.text_input("产品编号", value=product['pn'])
                        new_module = st.text_input("模块名称", value=product['module_name'])
                        new_desc = st.text_area("描述", value=product['description'])
                        
                        if st.form_submit_button("更新"):
                            with sqlite3.connect(CONN) as conn:
                                conn.execute("""
                                UPDATE Products SET pn=?, module_name=?, description=? WHERE id=?
                                """, (new_pn, new_module, new_desc, product['id']))
                                conn.commit()
                            st.success("产品已更新!")
                            st.rerun()
                        if st.form_submit_button("删除", type="secondary"):
                            with sqlite3.connect(CONN) as conn:
                                conn.execute("DELETE FROM Products WHERE id=?", (product['id'],))
                                conn.commit()
                            st.success("产品已删除!")
                            st.rerun()
    else:
        st.warning("暂无产品数据")
st.write("---")
st.subheader("Add Production Yield Data")
# 添加新的良率数据录入部分
with st.expander("添加生产良率数据"):
    with st.form("yield_form"):
        # 获取产品和工站数据
        with sqlite3.connect(CONN) as conn:
            products = pd.read_sql("SELECT pn, module_name FROM Products", conn)
            stations = pd.read_sql("SELECT name FROM Stations", conn)
        
        # 产品选择
        product_options = [f"{p['pn']} - {p['module_name']}" for _, p in products.iterrows()]
        product_choice = st.selectbox("选择产品*", product_options)
        
        # 工站选择
        station_choice = st.selectbox("选择工站*", stations['name'].tolist())
        
        # 日期代码 - 确保始终初始化date_code变量
        current_date = datetime.now()
        date_code = st.text_input("日期代码(YYWW)*", 
                    value=f"{current_date.strftime('%y')}{current_date.strftime('%W')}",
                    key="yield_form_date_code_input")  # 添加唯一key
        
        # 移除重复的date_code输入框
        # if st.session_state.get("yield_form_date_code")!="empty":
        #     date_code = st.text_input("日期代码(YYWW)*", 
        #                 value=f"{current_date.strftime('%y')}{current_date.strftime('%W')}")
                      
        
        # 数量输入
        col1, col2 = st.columns(2)
        with col1:
            good_count = st.number_input("生产数量*", min_value=0, value=0)
        with col2:
            bad_count = st.number_input("不良数量*", min_value=0, value=0)
        
        # 不良描述和改善措施
        defect_description = st.text_area("不良内容描述")
        improvement_measures = st.text_area("改善措施")
        
        # 添加图片和附件上传
        col3, col4 = st.columns(2)
        with col3:
            picture = st.file_uploader("上传图片", type=["jpg", "png", "jpeg"])
        with col4:
            attachment = st.file_uploader("上传附件", type=["pdf", "doc", "docx", "xlsx", "xls", "csv", "txt"])
        
        submitted = st.form_submit_button("提交")
        if submitted:
            if not all([product_choice, station_choice, date_code, good_count is not None, bad_count is not None]):
                st.error("请填写所有必填字段(*)")
            else:
                # 创建上传目录
                os.makedirs("uploads/productionyield", exist_ok=True)
                
                # 直接使用PN和工站名称
                product_pn = product_choice.split(" - ")[0]
                station_name = station_choice
                
                # 插入数据
                with sqlite3.connect(CONN) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                    INSERT INTO YieldData (
                        product_id, station_id, date_code, 
                        good_count, bad_count, defect_description,
                        improvement_measures, picture, attachment, create_date,pn,station
                    ) VALUES (
                        (SELECT id FROM Products WHERE pn = ?), 
                        (SELECT id FROM Stations WHERE name = ?), 
                        ?, ?, ?, ?, ?, ?, ?, ?,?,?
                    )
                    """, (
                        product_pn, station_name, date_code,
                        good_count, bad_count, defect_description,
                        improvement_measures, None, None, datetime.now().date(),product_pn,station_name,
                    ))
                    record_id = cursor.lastrowid
                    
                    # 处理文件上传
                    picture_path = None
                    if picture:
                        picture_path = f"uploads/productionyield/{record_id}_{picture.name}"
                        with open(picture_path, "wb") as f:
                            f.write(picture.getbuffer())
                    
                    attachment_path = None
                    if attachment:
                        attachment_path = f"uploads/productionyield/{record_id}_{attachment.name}"
                        with open(attachment_path, "wb") as f:
                            f.write(attachment.getbuffer())
                    
                    # 更新记录的文件路径
                    cursor.execute("""
                    UPDATE YieldData 
                    SET picture=?, attachment=?
                    WHERE id=?
                    """, (picture_path, attachment_path, record_id))
                    
                    conn.commit()
                st.success("良率数据添加成功!")
                st.session_state.yield_form_date_code = "empty"

# 在表单外重新定义date_code输入框，使用session_state保持状态
# 显示已输入的YieldData
st.write("---")
st.subheader("已录入的生产良率数据")

with sqlite3.connect(CONN) as conn:
    # 测试SQL语句是否返回数据
    test_query = "SELECT COUNT(*) FROM YieldData"
    count = conn.execute(test_query).fetchone()[0]
    st.write(f"YieldData表中现有记录数: {count}")
    
    # 获取完整的YieldData数据，关联产品和工站名称
    yield_data = pd.read_sql("""
    SELECT y.id, p.pn, p.module_name, s.name as station_name, 
           y.date_code, y.production_count, y.bad_count,
           y.defect_description, y.improvement_measures,
           y.picture, y.attachment, y.create_date
    FROM YieldData y
    LEFT JOIN Products p ON y.product_id = p.id
    LEFT JOIN Stations s ON y.station_id = s.id
    ORDER BY y.id DESC
    LIMIT 3
    """, conn)

if not yield_data.empty:
    st.write(f"Latest {len(yield_data)} 条良率记录")
    for _, row in yield_data.iterrows():
        st.write("---")
        # 使用columns布局显示基本信息
        col1, col2 = st.columns([4, 1])
        with col1:
            st.write(f"**id**: {row['id']} - **创建日期**: {row['create_date']}")
            st.write(f"**产品**: {row['pn']} - {row['module_name']}")
            st.write(f"**工站**: {row['station_name']}")
            st.write(f"**日期代码**: {row['date_code']}")
            st.write(f"**生产数量**: {row['production_count']}")
            st.write(f"**不良数量**: {row['bad_count']}")
            if row['defect_description']:
                st.write(f"**不良内容**: {row['defect_description']}")
            if row['improvement_measures']:
                st.write(f"**改善措施**: {row['improvement_measures']}")
        
        with col2:
            with st.popover("操作"):
                with st.form(f"edit_yield_{row['id']}"):
                    date_code = st.text_input("日期代码", value=row['date_code'])
                    good_count = st.number_input("生产数量", value=row['production_count'], min_value=0)
                    bad_count = st.number_input("不良数量", value=row['bad_count'], min_value=0)
                    defect_description = st.text_area("不良内容描述", value=row['defect_description'])
                    improvement_measures = st.text_area("改善措施", value=row['improvement_measures'])
                    
                    if st.form_submit_button("更新数据"):
                        with sqlite3.connect(CONN) as conn:
                            conn.execute("""
                            UPDATE YieldData SET
                                date_code = ?,
                                good_count = ?,
                                bad_count = ?,
                                defect_description = ?,
                                improvement_measures = ?
                            WHERE id = ?
                            """, (
                                date_code, good_count, bad_count,
                                defect_description, improvement_measures,
                                row['id']
                            ))
                            conn.commit()
                        st.success("良率数据已更新!")
                        st.rerun()
                    
                    if st.form_submit_button("删除记录", type="secondary"):
                        with sqlite3.connect(CONN) as conn:
                            conn.execute("DELETE FROM YieldData WHERE id = ?", (row['id'],))
                            conn.commit()
                        st.success("良率数据已删除!")
                        st.rerun()
else:
    st.warning("暂无生产良率数据")

