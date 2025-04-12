
import streamlit as st
import sqlite3
CONN='database.db'

pages = {
    
    "SPC": [
        st.Page("read.py", title="Read from Excel"),
        st.Page("draw.py", title="Draw SPC Chart"),
    ],
    "Quality": [
        #st.Page("8D.py", title="8D Customer Complaints"),
        #st.Page("VCAR.py", title="VCAR Complaints Supplier"),
        #st.Page("MVT.py", title="MVT PCN Tracking"),
        st.Page("8D2.py", title="8D Complaints"),
        st.Page("MVT2.py", title="MVT PCN Tracking"),
        

        
    ],
    "Production": [
        st.Page("productionadd.py", title="Add Stations/Module"),
        st.Page("loadyieldid.py", title="Load Production id="),
        st.Page("reviewyield2.py", title="Review Yield Data2"),
        
        
    ],
}

SPC_DATA = {
    "Y Direction Measurement on Front Rail Z3": [1,4,5,0,0.075,'03232-0010-000'],
    "Y Direction Measurement on Front Rail Z4": [1,5,5,0,0.075,'03232-0010-000'],
    "Lower Front Rail Height Cold Z1 ": [1,12,5,227.81,227.91,'03244-0010-000'],
    "Lower Front Rail Height Cold Z1 6": [1,13,5,227.81,227.91,'03244-0010-000'],
}# 数据格式为：[SN列, data列, 起始行, LSL, USL,PN匹配]
SPC_PN = [2, 1]  # [行, 列] 1-based索引
SPC_SIGMA = [0.075, 0.075]  # 标准差
# PN到Module Name的映射字典
PN_TO_MODULE = {
    "03232-0010-000": "Elite Standard Indexer",
    "03244-0010-000": "PowerComm CTX7 Indexer",
    "03245-0010-000": "PowerNext CTX8 Indexer",
    # 可以继续添加更多映射
}
SPC_Group = 5  # 每组数据个数
