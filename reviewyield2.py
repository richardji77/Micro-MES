import streamlit as st
import pandas as pd
import sqlite3

from datetime import datetime

from config import SPC_DATA, PN_TO_MODULE, CONN

# 数据库连接
conn = sqlite3.connect(CONN)
if 'username' not in st.session_state or not st.session_state.username:
    st.warning("请先登录系统")
    st.stop()
# 获取PN和Module列表
pn_module_list = [(pn, module) for pn, module in PN_TO_MODULE.items()]

# 创建查询界面
st.subheader("生产数据分析")

# 第一行：选择框和搜索框
col1, col2 = st.columns([2, 3])
with col1:
    # 添加"All"选项
    pn_module_list = [("All", "All")] + pn_module_list
    selected_pn, selected_module = st.selectbox(
        "选择PN和Module",
        options=pn_module_list,
        format_func=lambda x: f"{x[0]} - {x[1]}" if x[0] != "All" else "All - 全部PN",
        index=0  # 默认选中第一个选项(All)
    )
with col2:
    search_text = st.text_input("搜索PN或Module")

# 第二行：日期范围选择
col3, col4 = st.columns(2)
with col3:
    start_date = st.date_input("开始日期", datetime.now() - pd.Timedelta(days=30))
    start_yyww = start_date.strftime("%y%W")
    st.write(f"开始周: {start_yyww}")
with col4:
    end_date = st.date_input("结束日期", datetime.now()) 
    end_yyww = end_date.strftime("%y%W")
    st.write(f"结束周: {end_yyww}")

if st.button("查询数据"):
    # 构建查询条件
    query = """
    SELECT date_code, SUM(good_count) as total_quantity, 
           SUM(bad_count) as total_defects
    FROM yielddata
    WHERE date_code >= ? AND date_code <= ?
    """
    params = [start_yyww, end_yyww]
    
    # 添加PN/Module筛选条件
    if search_text:
        query += " AND (pn LIKE ? OR pn LIKE ?)"
        search_term = f"%{search_text.lower().replace(' ', '')}%"
        params.extend([search_term, search_term])
    elif selected_pn != "All":  # 只有当不是All时才添加PN条件
        query += " AND pn = ?"
        params.append(selected_pn)
    
    query += " GROUP BY date_code ORDER BY date_code"
    
    # 执行查询
    df = pd.read_sql(query, conn, params=params)
    
    if not df.empty:
        # 计算不良率
        df['defect_rate'] = df['total_defects'] / df['total_quantity']*100
        
        # 显示数据表格
        st.dataframe(df)
        
        # 使用Streamlit原生图表
        st.subheader("不良率趋势")
        st.line_chart(df.set_index('date_code')['defect_rate'])
        
        st.subheader("生产数量和不良数量")
        st.bar_chart(df.set_index('date_code')[['total_quantity', 'total_defects']])
        
        # 新增：各PN详细数据查询
        detail_query = """
        SELECT pn, station, date_code, 
               SUM(good_count) as quantity, 
               SUM(bad_count) as defect_count
        FROM yielddata
        WHERE date_code >= ? AND date_code <= ?
        """
        detail_params = [start_yyww, end_yyww]
        
        if search_text:
            detail_query += " AND (pn LIKE ? OR pn LIKE ?)"
            detail_params.extend([search_term, search_term])
        elif selected_pn != "All":
            detail_query += " AND pn = ?"
            detail_params.append(selected_pn)
            
        detail_query += " GROUP BY pn, station, date_code ORDER BY pn, date_code"
        
        # 获取详细数据
        detail_df = pd.read_sql(detail_query, conn, params=detail_params)
        
        if not detail_df.empty:
            st.subheader("各PN详细数据")
            st.dataframe(detail_df)
            
            # 新增：叠加柱状图
            st.subheader("各PN生产数量(叠加)")
            st.bar_chart(detail_df.pivot_table(
                index='date_code', 
                columns='pn', 
                values='quantity', 
                aggfunc='sum'
            ), use_container_width=True)
            
            st.subheader("各PN不良数量(叠加)") 
            st.bar_chart(detail_df.pivot_table(
                index='date_code',
                columns='pn',
                values='defect_count',
                aggfunc='sum'
            ), use_container_width=True)

        # 修改：不良原因和改善措施查询
        st.subheader("不良内容详情")
        defect_query = """
        SELECT id, pn,station, date_code, defect_description, improvement_measures, SUM(bad_count) as defect_count
        FROM yielddata
        WHERE date_code >= ? AND date_code <= ? AND bad_count > 0
        """
        defect_params = [start_yyww, end_yyww]
        
        if search_text:
            defect_query += " AND (pn LIKE ? OR pn LIKE ?)"
            defect_params.extend([search_term, search_term])
        elif selected_pn != "All":
            defect_query += " AND pn = ?"
            defect_params.append(selected_pn)
            
        defect_query += " GROUP BY pn, date_code, defect_description, improvement_measures ORDER BY pn, date_code"
        
        defect_df = pd.read_sql(defect_query, conn, params=defect_params)
        
        if not defect_df.empty:
            for index, row in defect_df.iterrows():
                with st.expander(f"ID: {row['id']} |PN: {row['pn']} | 周: {row['date_code']} | 不良数量: {row['defect_count']}"):
                    st.write(f"不良原因: {row['defect_description']}")
                    st.write(f"改善措施: {row['improvement_measures']}")
        else:
            st.write("未找到匹配的不良记录")

    else:
        st.warning("没有找到匹配的数据")

    conn.close()  # 确保在最后关闭连接

# 添加生产数据表结构
def init_production_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS productiondata (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pn TEXT,
        modulename TEXT,
        username TEXT,
        createdate TEXT,
        date_code TEXT,
        good_count INTEGER,
        bad_count INTEGER,
        defect_description TEXT,
        improvement_measures TEXT,
        remark TEXT
    )
    ''')
    
    # 生成模拟数据
    from datetime import datetime, timedelta
    import random
    
    # 检查是否已有数据
    if cursor.execute("SELECT COUNT(*) FROM productiondata").fetchone()[0] == 0:
        users = ['张三', '李四', '王五']
        defect_descriptions = ['材料问题', '工艺问题', '设备故障', '操作失误', '设计缺陷']
        improvement_measuress = ['更换供应商', '调整参数', '设备维护', '加强培训', '设计优化']
        
        # 生成过去8周的数据
        for i in range(8):
            week = datetime.now() - timedelta(weeks=8-i)
            yyww = week.strftime("%y%W")
            
            for pn, module in PN_TO_MODULE.items():
                quantity = random.randint(50, 200)
                defect_count = random.randint(0, quantity//10)
                
                cursor.execute('''
                INSERT INTO productiondata 
                (pn, modulename, username, createdate, YYWW, quantity, defect_count, defect_description, improvement_measures, remark)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    pn,
                    module,
                    random.choice(users),
                    week.strftime('%Y-%m-%d'),
                    yyww,
                    quantity,
                    defect_count,
                    random.choice(defect_descriptions) if defect_count > 0 else '',
                    random.choice(improvement_measuress) if defect_count > 0 else '',
                    ''
                ))
    
    conn.commit()
    conn.close()
# 在文件末尾调用初始化函数
init_production_db()

