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

# 确保8D报告表存在
def init_tracking_table():
    with sqlite3.connect(CONN) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS Tracking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            No TEXT NOT NULL,
            customer TEXT NOT NULL,
            supplier TEXT NOT NULL,
            description TEXT NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE,
            status TEXT CHECK(status IN ('open', 'closed')) NOT NULL,
            NG_Picture TEXT,
            Good_Picture TEXT,
            report_file TEXT,
            username TEXT NOT NULL,
            create_date DATE NOT NULL,
            type TEXT DEFAULT '8D' NOT NULL
        )
        """)

# 获取当前年份的所有8D报告
def get_all_reports(year=None):
    year = year or datetime.now().year
    with sqlite3.connect(CONN) as conn:
        query = """
        SELECT No, customer, supplier, description, status, start_date, end_date 
        FROM Tracking 
        WHERE strftime('%Y', start_date) = ? AND type = 'MVT'
        ORDER BY start_date DESC
        """
        return pd.read_sql(query, conn, params=(str(year),))

# 获取单个报告的详细信息
def get_report_details(report_no):
    with sqlite3.connect(CONN) as conn:
        query = "SELECT * FROM Tracking WHERE No = ?"
        return conn.execute(query, (report_no,)).fetchone()

# 保存上传的文件
def save_uploaded_file(uploaded_file, report_no):
    os.makedirs("MVT_reports", exist_ok=True)
    file_path = os.path.join("MVT_reports", f"{report_no}_{uploaded_file.name}")
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return file_path

# 初始化表
init_tracking_table()

# 主界面


st.subheader("MVT报告跟踪系统")


# 创建新报告 - 保持原有样式
with st.expander("创建新MVT报告"):
    with st.form("new_report_form"):
        # 添加报告编号输入框
        report_no = st.text_input(
            "报告编号*", 
            value=f"MVT-{datetime.now().strftime('%y%m')}-",
            help="格式: MVT-YYMM-序号 (例如: MVT-2401-01)"
        )
        customer = st.text_input("客户名称*","NA")
        supplier = st.text_input("供应商名称*","NA")
        description = st.text_area("问题描述*")
        start_date = st.date_input("开始日期*", datetime.now())
        status = st.selectbox("状态*", ["open", "closed"])
        ng_pic = st.file_uploader("不良照片", type=["jpg", "png", "jpeg"])
        good_pic = st.file_uploader("良品照片", type=["jpg", "png", "jpeg"])
        report_file = st.file_uploader("报告附件", type=["pdf", "doc", "docx"])
        
        submitted = st.form_submit_button("提交")
        if submitted:
            if not all([report_no, customer, supplier, description]):
                st.error("请填写所有必填字段(*)")
            elif not report_no.startswith("MVT-"):
                st.error("报告编号必须以'MVT-'开头")
            else:
                # 保存文件
                ng_path = save_uploaded_file(ng_pic, report_no) if ng_pic else None
                good_path = save_uploaded_file(good_pic, report_no) if good_pic else None
                report_path = save_uploaded_file(report_file, report_no) if report_file else None
                
                # 保存到数据库
                with sqlite3.connect(CONN) as conn:
                    # 检查编号是否已存在
                    existing = conn.execute("SELECT No FROM Tracking WHERE No = ?", (report_no,)).fetchone()
                    if existing:
                        st.error("该报告编号已存在，请使用其他编号")
                    else:
                        conn.execute("""
                        INSERT INTO Tracking (
                            No, customer, supplier, description, 
                            start_date, status, NG_Picture, 
                            Good_Picture, report_file, username, create_date,
                            type
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            report_no, customer, supplier, description,
                            start_date, status, ng_path,
                            good_path, report_path, st.session_state.username, 
                            datetime.now().date(),
                            'MVT'  # 固定为8D类型
                        ))
                        conn.commit()
                st.success("MVT报告创建成功!")

# 查看现有报告
st.write("---")
col1, col2 = st.columns([1, 3])

with col1:
    st.subheader("现有MVT报告")
with col2:
    year = st.selectbox("选择年份", range(2024, datetime.now().year+1), index=datetime.now().year-2024)

reports = get_all_reports(year)

if not reports.empty:
    for _, report in reports.iterrows():
        # 为open状态添加emoji标识
        status_icon = "🔥" if report['status'] == 'open' else "✅"
        
        with st.expander(f"{status_icon} {report['No']} - {report['customer']} - {report['supplier']} - {report['description'][:60]}...【{report['status']}】"):
            report_details = get_report_details(report['No'])
            
            if report_details:
                # 显示报告详情
                st.write(f"报告编号: {report_details[1]}")  # No字段不可编辑
                
                # 编辑功能
                with st.form(f"edit_form_{report['No']}"):
                    customer = st.text_input("客户名称", value=report_details[2])
                    supplier = st.text_input("供应商名称", value=report_details[3])
                    description = st.text_area("问题描述", value=report_details[4])
                    start_date = st.date_input("开始日期", 
                                            datetime.strptime(report_details[5], "%Y-%m-%d").date())
                    end_date = st.date_input("结束日期", 
                                           datetime.strptime(report_details[6], "%Y-%m-%d").date() 
                                           if report_details[6] else None)
                    status = st.selectbox("状态", ["open", "closed"], 
                                        index=0 if report_details[7] == "open" else 1)
                    
                    # 图片和文件更新
                    new_ng_pic = st.file_uploader("更新不良照片", type=["jpg", "png", "jpeg"])
                    new_good_pic = st.file_uploader("更新良品照片", type=["jpg", "png", "jpeg"])
                    new_report_file = st.file_uploader("更新报告附件", type=["pdf", "doc", "docx"])
                    
                    if st.form_submit_button("更新报告", type="primary"):
                        # 保存新上传的文件
                        ng_path = save_uploaded_file(new_ng_pic, report['No']) if new_ng_pic else report_details[8]
                        good_path = save_uploaded_file(new_good_pic, report['No']) if new_good_pic else report_details[9]
                        report_path = save_uploaded_file(new_report_file, report['No']) if new_report_file else report_details[10]
                        
                        with sqlite3.connect(CONN) as conn:
                            conn.execute("""
                            UPDATE Tracking 
                            SET customer=?, supplier=?, description=?, 
                                start_date=?, end_date=?, status=?,
                                NG_Picture=?, Good_Picture=?, report_file=?
                            WHERE No = ?
                            """, (
                                customer, supplier, description,
                                start_date, end_date, status,
                                ng_path, good_path, report_path,
                                report['No']
                            ))
                            conn.commit()
                        st.success("报告已更新!")
                        st.rerun()
                
                # 显示图片和附件下载
                col1, col2 = st.columns(2)
                with col1:
                    if report_details[8]:
                        st.image(report_details[8], caption="不良照片", width=300)
                    if report_details[9]:
                        st.image(report_details[9], caption="良品照片", width=300)
                
                with col2:
                    if report_details[10]:
                        with open(report_details[10], "rb") as file:
                            st.download_button(
                                label="下载报告附件",
                                data=file,
                                file_name=os.path.basename(report_details[10]),
                                mime="application/octet-stream"
                            )
                
                # 合并为一个编辑表单（删除下面这个重复的表单）
                # with st.form(f"edit_form_{report['No']}"):
                #     new_status = st.selectbox("更新状态", ["open", "closed"], 
                #                             index=0 if report_details[7] == "open" else 1)
                #     new_end_date = st.date_input("结束日期", 
                #                                 datetime.strptime(report_details[6], "%Y-%m-%d").date() 
                #                                 if report_details[6] else None)
                    
                #     if st.form_submit_button("更新报告"):
                #         with sqlite3.connect(CONN) as conn:
                #             conn.execute("""
                #             UPDATE Tracking 
                #             SET status = ?, end_date = ?
                #             WHERE No = ?
                #             """, (new_status, new_end_date, report['No']))
                #             conn.commit()
                #         st.success("报告已更新!")
                #         st.rerun()
else:
    st.warning("当前年份没有8D报告记录")

