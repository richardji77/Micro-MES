import streamlit as st
import pandas as pd
import sqlite3
import os
#import matplotlib.pyplot as plt  # Change this line
from config import SPC_DATA, PN_TO_MODULE,SPC_Group,CONN
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 数据库连接
conn = sqlite3.connect(CONN)
if 'username' not in st.session_state or not st.session_state.username:
    st.warning("请先登录系统")
    st.stop()  # 停止执行后续代码
# 获取有足够数据的PN列表
pn_options = []
for pn in {config[5] for config in SPC_DATA.values()}:
    count = conn.execute("SELECT COUNT(*) FROM measurement_data WHERE pn=?", (pn,)).fetchone()[0]
    #st.write(f"PN: {pn}, Count: {count}")
    if count >= 50:
        module = PN_TO_MODULE.get(pn, "Unknown")
        pn_options.append((pn, f"{pn} ({module})"))

if not pn_options:
    st.warning("没有找到包含足够数据的PN记录")
else:
    # 第一行：选择PN和参数
    col1, col2,col3 = st.columns(3)
    with col1:
        selected_pn = st.selectbox("选择PN", options=pn_options, format_func=lambda x: x[1])
    with col2:
        params = [name for name, config in SPC_DATA.items() if config[5] == selected_pn[0]]
        selected_param = st.selectbox("选择参数", params)

    # 查询可用月份
    month_query = """
    SELECT DISTINCT strftime('%Y-%m', measurement_date) as month 
    FROM measurement_data 
    WHERE pn=? AND parameter_name=?
    GROUP BY month
    HAVING COUNT(*) >= 50
    ORDER BY month DESC
    """
    available_months = pd.read_sql(month_query, conn, params=(selected_pn[0], selected_param))['month'].tolist()
    
    if not available_months:
        st.error("选定的PN和参数没有包含足够数据的月份")
    else:
        # 选择月份
        with col3:
            selected_month = st.selectbox("选择月份", available_months)

        if st.button("生成SPC图表"):
            # 从数据库获取数据（添加月份条件）
            query = """
            SELECT DISTINCT sn, measurement_value 
            FROM measurement_data 
            WHERE pn=? AND parameter_name=? AND strftime('%Y-%m', measurement_date)=?
            ORDER BY measurement_date
            """
            df = pd.read_sql(query, conn, params=(selected_pn[0], selected_param, selected_month))
            conn.close()
            if len(df) >= 50:
                # 计算X-bar和R值
                df['subgroup'] = (df.index // SPC_Group) + 1  # 5个数据为一组
                xbar_r = df.groupby('subgroup').agg(
                    xbar=('measurement_value', 'mean'),
                    r=('measurement_value', lambda x: max(x) - min(x))
                )
                
                # 创建Plotly图表
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                              subplot_titles=(f'X-bar Chart for {selected_pn[1]} - {selected_param}',
                                            f'R Chart for {selected_pn[1]} - {selected_param}'))
                
                # X-bar图
                overall_mean = df['measurement_value'].mean()
                std_dev = df['measurement_value'].std()
                ucl = overall_mean + 3 * std_dev
                lcl = overall_mean - 3 * std_dev
                
                fig.add_trace(go.Scatter(
                    x=xbar_r.index,
                    y=xbar_r['xbar'],
                    mode='lines+markers',
                    name='X-bar',
                    line=dict(color='blue')
                ), row=1, col=1)
                
                # 添加控制线
                fig.add_hline(y=overall_mean, line=dict(color='red', dash='dash'),
                             annotation_text=f'AVG: {overall_mean:.3f}', row=1, col=1)
                fig.add_hline(y=ucl, line=dict(color='green', dash='dash'),
                             annotation_text=f'UCL: {ucl:.3f}', row=1, col=1)
                fig.add_hline(y=lcl, line=dict(color='green', dash='dash'),
                             annotation_text=f'LCL: {lcl:.3f}', row=1, col=1)
                
                # R图
                r_mean = xbar_r['r'].mean()
                fig.add_trace(go.Scatter(
                    x=xbar_r.index,
                    y=xbar_r['r'],
                    mode='lines+markers',
                    name='R',
                    line=dict(color='green')
                ), row=2, col=1)
                
                fig.add_hline(y=r_mean, line=dict(color='red', dash='dash'),
                             annotation_text=f'AVG: {r_mean:.3f}', row=2, col=1)
                
                # 更新布局
                fig.update_layout(
                    height=800,
                    showlegend=True,
                    hovermode='x unified'
                )
                
                # 更新y轴标签
                fig.update_yaxes(title_text="AVERAGE", row=1, col=1)
                fig.update_yaxes(title_text="R VALUE", row=2, col=1)
                
                st.plotly_chart(fig, use_container_width=True)
                
                # 计算并显示CPK
                param_config = next((v for k, v in SPC_DATA.items() 
                                   if k == selected_param and v[5] == selected_pn[0]), None)
                if param_config:
                    lsl = param_config[3]  # 第4位是LSL
                    usl = param_config[4]  # 第5位是USL
                    
                    if usl is not None and lsl is not None:
                        sigma = df['measurement_value'].std()
                        mean = df['measurement_value'].mean()
                        cpu = (usl - mean) / (3 * sigma) if sigma != 0 else float('nan')
                        cpl = (mean - lsl) / (3 * sigma) if sigma != 0 else float('nan')
                        cpk = min(cpu, cpl)
                        
                        st.markdown(f"""
                        **CPK计算结果**  
                        - 参数: {selected_param}  
                        - PN: {selected_pn[0]}  
                        - 平均值: {mean:.4f}  
                        - 标准差: {sigma:.4f}  
                        - USL: {usl:.4f}  
                        - LSL: {lsl:.4f}  
                        - CPK: {cpk:.4f}  
                        """)
                    else:
                        st.warning("该参数未设置规格上下限，无法计算CPK")
                else:
                    st.warning(f"未找到参数 {selected_param} 和 PN {selected_pn[0]} 的配置")

            else:
                st.error(f"选定的参数在{selected_month}没有足够的数据点(需要至少50个)")

# 将conn.close()移到文件最末尾

   

