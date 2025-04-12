import streamlit as st
from config import pages
import sqlite3

from config import CONN

def login(username, password):
    username = username.strip().lower()
    password = password.strip().lower()
    
    try:
        with sqlite3.connect(CONN) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE LOWER(username)=? AND LOWER(password)=?", 
                         (username, password))
            return cursor.fetchone() is not None
    except sqlite3.Error as e:
        st.error(f"数据库错误: {str(e)}")
        return False

def logout():
    # 清除session状态已在app.py中处理
    pass


# 初始化session状态
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None

# 设置页面为宽屏模式
st.set_page_config(layout="wide")

# 登录表单
if not st.session_state.logged_in:
    st.header("用户登录")  # 移动到主窗口
    username = st.text_input("用户名")
    password = st.text_input("密码", type="password")
    if st.button("登录"):
        if login(username, password):
            st.session_state.logged_in = True
            st.session_state.username = username
            st.rerun()
        else:
            st.error("用户名或密码错误")
else:
    # 主页面内容
    st.header("Welcome to the Micro MES")
    st.logo("static/logo.jpeg")
    
    # 在侧边栏显示登录状态
    with st.sidebar:
        st.success(f"已登录: {st.session_state.username}")
        if st.button("登出"):
            logout()
            st.session_state.logged_in = False
            st.session_state.username = None
            st.rerun()


pg = st.navigation(pages)
pg.run()