import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime
from config import CONN
from data import *
# 数据库连接
conn = sqlite3.connect(CONN)
if 'username' not in st.session_state or not st.session_state.username:
    st.warning("请先登录系统")
    st.stop()

tracking("8D2")
