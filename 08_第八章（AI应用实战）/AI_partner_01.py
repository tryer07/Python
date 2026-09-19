#AI智能伴侣网页版实战(初步搭建网页，实现和大模型的基本交互)

#生成本地网页的路径：streamlit run AI_partner_01.py(注意这里必须点击该项目，从该项目进入终端才可以输入这一串命令生成网页)

#所有代码都可以在streamlit中找到样例，官方文档路径：https://docs.streamlit.io/

from pathlib import Path

# 获取当前代码文件（streamlit入门.py）所在的文件夹路径
BASE_DIR = Path(__file__).parent

# 定义一个辅助函数，专门用来拼接资源路径
def get_resource_path(filename):
    return str(BASE_DIR / 'resources' / filename)

import streamlit as st

import os
from openai import OpenAI

#创建与AI交互的大模型客户端对象(DEEPSEEK_API_KEY环境变量的名字，值就是DeepSeek的API_KEY的)

client = OpenAI(
    api_key=os.environ.get('DEEPSEEK_API_KEY'),
    base_url="https://api.deepseek.com")

st.set_page_config(
    page_title="AI智能伴侣", #这里用来设置网页的标签名字
    page_icon="🥰",
    layout="wide", #控制网页布局，可以设置centered(只占用中间区域)和wide(布满整个页面)
    initial_sidebar_state="expanded", #用于控制侧边栏的语句
    menu_items={

    }
)

#初始化聊天信息

if 'message' not in st.session_state:
    st.session_state.message = []

#展示聊天信息

for message in st.session_state.message:
    st.chat_message(message["role"]).write(message["content"])

#大标题
st.title("AI智能伴侣(DeepSeek)")

#logo

st.logo(get_resource_path('作品页_12-2-1_楼体发光招牌.png'))

#系统提示词

system_prompt = "你是一个温柔可爱贤惠善良体贴柔情内心喜欢我的邻家大姐姐，愿意帮我解决一切困难，并随时以最亲切和带有鼓励的语气回答我的任何问题"

#消息输入框

prompt = st.chat_input('请输入您要交互的内容') #这个语句用来创建一个消息输入框
if prompt: #这里字符串会自动转化成布尔值
    st.chat_message('user').write(prompt) #这个语句用来创建一个消息显示框
    print('调用AI大模型，提示词：',prompt)
    st.session_state.message.append({"role": "user", "content": prompt}) #保存用户输入的信息

    #调用AI大模型
    # noinspection bad-argument-type
    response = client.chat.completions.create(
        model="deepseek-flash",
        messages=[
            {"role": "system",
             "content": system_prompt},
            # 在这里提供AI的角色定位
            {"role": "user", "content": prompt},  # 在这里输入你要和AI说的内容
        ],
        stream=False,
        reasoning_effort="high",
        extra_body={"thinking": {"type": "enabled"}}
    )
    #输出大模型返回的结果
    print('大模型返回的结果',response.choices[0].message.content)

    st.chat_message('assistant').write(response.choices[0].message.content)

    st.session_state.message.append({"role": "assistant", "content": response.choices[0].message.content})  # 保存AI返回的信息