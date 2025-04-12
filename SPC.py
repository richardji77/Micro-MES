import streamlit as st
import pandas as pd
import os
import sqlite3
import shutil
from datetime import datetime
from config import SPC_DATA,SPC_PN
from config import PN_TO_MODULE

def read_and_process_files():
    # 检查uploads文件夹下是否有Excel文件
    excel_files = [f for f in os.listdir('uploads') if f.endswith(('.xlsx', '.xls'))]
    if not excel_files:
        st.warning("未发现Excel文件在uploads文件夹下面")
        return
    
    # 创建必要的目录
    os.makedirs('uploads/success', exist_ok=True)
    
    # 初始化错误日志
    error_log = []
    total_processed = 0
    
    # 获取当前日期
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    # 数据库连接
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS measurement_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        parameter_name TEXT,
        pn TEXT,
        sn TEXT,
        measurement_value REAL,
        measurement_date TEXT,
        lower_limit REAL,
        upper_limit REAL
    )
    ''')
    
    # 处理每个文件
    for filename in os.listdir('uploads'):
        if filename.endswith(('.xlsx', '.xls')):
            filepath = os.path.join('uploads', filename)
            records_processed = 0
            
            try:
                df = pd.read_excel(filepath)
                
                # 读取PN信息时会这样处理：
                # 读取PN信息 - 修改后的处理逻辑
                pn_row = SPC_PN[0] - 1
                pn_col = SPC_PN[1] - 1
                
                # 添加调试信息
                #st.write(f"正在读取文件: {filename}")
                #st.write(f"数据框形状: {df.shape}")  # 显示行列数
                #st.write(f"尝试读取位置: 行{pn_row+1} 列{pn_col+1}")
                
                # 更严格的空值检查
                try:
                    pn_value = df.iat[pn_row, pn_col]  # 使用iat更快
                    if pd.isna(pn_value):  # 检查是否为空值
                        #st.warning(f"A1单元格为空或无效，文件名: {filename}{df.iat[-1,1]}")
                        # 读取PN信息 - 最终解决方案
                        pn = "Unknown"
                        try:
                            # 方案1：从A1单元格读取
                            cell_value = df.iat[SPC_PN[0]-1, SPC_PN[1]-1]
                            if pd.notna(cell_value):
                                pn = str(cell_value).strip()
                        
                            # 方案2：从文件名提取（如果A1无效）
                            if pn == "Unknown":
                                import re
                                filename_pn = re.search(r'(\d{5}-\d{4}-\d{3})', filename)
                                pn = filename_pn.group(1) if filename_pn else "Unknown"
                                
                            st.write(f"最终使用的PN值: {pn}")
                        except Exception as e:
                            st.error(f"PN读取失败: {str(e)}")
                    else:
                        pn = str(pn_value).strip()  # 去除前后空格
                        st.write(f"成功读取PN值: {pn}")
                except Exception as e:
                    st.error(f"读取PN失败: {str(e)}")
                    pn = "Unknown"
                
                for param_name, config in SPC_DATA.items():
                    try:
                        # 检查PN是否匹配
                        if pn != config[5]:  # 新增的PN匹配值在索引5位置
                            continue
                            
                        sn_col = config[0] - 1
                        value_col = config[1] - 1
                        start_row = config[2] - 1
                        lower = config[3]
                        upper = config[4]
                        
                        # 检查列索引
                        if sn_col >= len(df.columns) or value_col >= len(df.columns):
                            raise ValueError(f"列索引超出范围: SN列{config[0]}, 值列{config[1]}")
                            
                        for i in range(start_row, len(df)):
                            try:
                                sn = str(df.iloc[i, sn_col])
                                value = float(df.iloc[i, value_col])
                                
                                cursor.execute('''
                                INSERT INTO measurement_data 
                                (parameter_name, pn, sn, measurement_value, measurement_date, lower_limit, upper_limit)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                                ''', (param_name, pn, sn, value, current_date, lower, upper))
                                records_processed += 1
                                
                            except Exception as e:
                                error_log.append(f"{filename} - 行{i+1}: {str(e)}")
                                
                    except Exception as e:
                        error_log.append(f"{filename} - 参数{param_name}: {str(e)}")
                
                # 成功处理后移动文件
                if records_processed > 0:
                    shutil.move(filepath, os.path.join('uploads/success', filename))
                    st.success(f"""
                    {filename} 成功写入 {records_processed} 条记录
                    PN: {pn}
                    处理参数: {param_name}
                    """)
                    total_processed += records_processed
                
            except Exception as e:
                error_log.append(f"{filename}: {str(e)}")
    
    # 写入错误日志 - 修改为CSV格式
    if error_log:
        import csv
        error_file = 'uploads/error_log.csv'
        file_exists = os.path.isfile(error_file)
        
        with open(error_file, 'a', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(['Timestamp', 'Filename', 'Error'])  # 写入表头
            
            for error in error_log:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                # 分割错误信息为文件名和错误详情
                if ' - ' in error:
                    err_filename, err_detail = error.split(' - ', 1)
                else:
                    err_filename, err_detail = filename, error
                writer.writerow([timestamp, err_filename, err_detail])
                
        st.warning(f"处理完成，但有 {len(error_log)} 个错误，详见 {error_file}")
    
    conn.commit()
    conn.close()
    
    if total_processed > 0 and not error_log:
        st.success(f"所有文件处理完成，共写入 {total_processed} 条记录")



st.subheader("SPC Control|Read from Excel")
st.write("Pls upload T&A Excel file into /uploads")
if st.button("Read and Process Files"):
    read_and_process_files()

