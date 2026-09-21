#AI智能伴侣网页版(侧边栏制作)

#生成本地网页的路径：streamlit run AI_partner_04.py(注意这里必须点击该项目，从该项目进入终端才可以输入这一串命令生成网页)

#所有代码都可以在streamlit中找到样例，官方文档路径：https://docs.streamlit.io/

import re
import json
import os
from pathlib import Path

import streamlit as st
from openai import OpenAI

# ========== 常量定义 ==========

BASE_DIR = Path(__file__).parent
SAVE_DIR = Path(r'D:\Python\历史会话存档处')
SAVE_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_NICK_NAME = '木婉清'
DEFAULT_NATURE = '高冷傲娇心里一直默默暗恋用户，却由于害羞从未开口言明'

SYSTEM_PROMPT = """
        你叫%s，现在是用户的真实伴侣，请完全代入角色
        规则：
            1.每次回复一条消息
            2.匹配用户的语言
            3.做他的知音，和他拥有灵魂级别的共鸣
            4.像微信聊天一样正常回复他的消息
            5.回复内容要符合角色性格定位
            6.用符合伴侣的方式说话
        伴侣性格：
           %s
        严格遵守以上规则，不要违背角色定位
"""

# ========== 页面配置（必须是第一个Streamlit命令） ==========

st.set_page_config(
    page_title="AI智能伴侣",
    page_icon="🥰",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={}
)

st.title("AI智能伴侣(DeepSeek)")

# ========== 辅助函数 ==========

def get_resource_path(filename):
    return str(BASE_DIR / 'resources' / filename)

def safe_filename(name):
    return re.sub(r'[\\/:*?"<>|]', '_', name)

def save_session(session_name, session_data):
    file_path = SAVE_DIR / f'{safe_filename(session_name)}.json'
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(session_data, f, ensure_ascii=False, indent=2)

def load_all_sessions():
    sessions = {}
    for file in sorted(SAVE_DIR.glob('*.json'), key=lambda f: f.stat().st_mtime):
        with open(file, 'r', encoding='utf-8') as f:
            sessions[file.stem] = json.load(f)
    return sessions

def delete_session_file(session_name):
    file_path = SAVE_DIR / f'{safe_filename(session_name)}.json'
    if file_path.exists():
        file_path.unlink()

def save_current():
    current = st.session_state.current_session
    if current and current in st.session_state.sessions:
        session_data = st.session_state.sessions[current]
        session_data['nick_name'] = st.session_state.nick_name
        session_data['nature'] = st.session_state.nature
        save_session(current, session_data)

# ========== 初始化客户端 ==========

client = OpenAI(
    api_key=os.environ.get('DEEPSEEK_API_KEY'),
    base_url="https://api.deepseek.com")

# ========== 会话状态初始化 ==========

if 'sessions' not in st.session_state:
    st.session_state.sessions = load_all_sessions()

if 'current_session' not in st.session_state:
    keys = list(st.session_state.sessions.keys())
    st.session_state.current_session = keys[0] if keys else None

if 'nick_name' not in st.session_state:
    st.session_state.nick_name = DEFAULT_NICK_NAME

if 'nature' not in st.session_state:
    st.session_state.nature = DEFAULT_NATURE

if st.session_state.current_session and st.session_state.current_session in st.session_state.sessions:
    session_data = st.session_state.sessions[st.session_state.current_session]
    st.session_state.nick_name = session_data.get('nick_name', DEFAULT_NICK_NAME)
    st.session_state.nature = session_data.get('nature', DEFAULT_NATURE)

# ========== 侧边栏 ==========

with st.sidebar:
    st.subheader("AI智能伴侣")
    nick_name = st.text_input('昵称', placeholder='请输入昵称', value=st.session_state.nick_name)
    if nick_name != st.session_state.nick_name:
        st.session_state.nick_name = nick_name
        save_current()
    nature = st.text_area('性格', placeholder='请输入性格', value=st.session_state.nature)
    if nature != st.session_state.nature:
        st.session_state.nature = nature
        save_current()

    st.divider()
    st.subheader("历史会话")

    new_session_name = st.text_input('新建会话', placeholder='输入会话名称后点击创建')
    if st.button('➕ 创建新会话'):
        if not new_session_name or not new_session_name.strip():
            st.warning('请输入会话名称')
        elif new_session_name in st.session_state.sessions:
            st.warning('该会话已存在，请直接切换')
        else:
            session_data = {
                'nick_name': st.session_state.nick_name,
                'nature': st.session_state.nature,
                'messages': []
            }
            st.session_state.sessions[new_session_name] = session_data
            st.session_state.current_session = new_session_name
            save_session(new_session_name, session_data)
            st.rerun()

    st.divider()

    if st.session_state.sessions:
        for session_name in st.session_state.sessions:
            col1, col2 = st.columns([4, 1])
            with col1:
                is_current = (session_name == st.session_state.current_session)
                label = f"✅ {session_name}（当前）" if is_current else f"💬 {session_name}"
                if st.button(label, key=f'switch_{session_name}', use_container_width=True):
                    if not is_current:
                        st.session_state.current_session = session_name
                        st.rerun()
            with col2:
                if st.button('🗑️', key=f'delete_{session_name}'):
                    del st.session_state.sessions[session_name]
                    delete_session_file(session_name)
                    if st.session_state.current_session == session_name:
                        keys = list(st.session_state.sessions.keys())
                        st.session_state.current_session = keys[0] if keys else None
                    st.rerun()
    else:
        st.info('暂无历史会话，请创建一个新会话开始聊天')

# ========== 聊天区域 ==========

if st.session_state.current_session and st.session_state.current_session in st.session_state.sessions:
    current_messages = st.session_state.sessions[st.session_state.current_session]['messages']
else:
    current_messages = []

for message in current_messages:
    st.chat_message(message["role"]).write(message["content"])

prompt = st.chat_input('请输入您要交互的内容')
if prompt:
    st.chat_message('user').write(prompt)
    print('调用AI大模型，提示词：', prompt)
    current_messages.append({"role": "user", "content": prompt})

    # noinspection PyTypeChecker
    response = client.chat.completions.create(
        model="deepseek-flash",
        messages=[
            {"role": "system",
             "content": SYSTEM_PROMPT % (st.session_state.nick_name, st.session_state.nature)},
            *current_messages
        ],
        stream=True,
        reasoning_effort="high",
        extra_body={"thinking": {"type": "enabled"}}
    )

    response_message = st.empty()
    full_response = ''
    for chunk in response:
        if chunk.choices[0].delta.content is not None:
            full_response += chunk.choices[0].delta.content
            response_message.chat_message('assistant').write(full_response)
    current_messages.append({"role": "assistant", "content": full_response})

    save_current()
