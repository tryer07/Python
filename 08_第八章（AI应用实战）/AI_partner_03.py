#AI智能伴侣网页版(侧边栏制作)

#生成本地网页的路径：streamlit run AI_partner_03.py(注意这里必须点击该项目，从该项目进入终端才可以输入这一串命令生成网页)

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

#标题

st.title("AI智能伴侣(DeepSeek)")


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

#昵称(这里是默认值，如果用户没有输入昵称，则使用这个默认值)

if 'nick_name' not in st.session_state:
    st.session_state.nick_name = '木婉清'

#性格(这里是默认值，如果用户没有输入性格，则使用这个默认值)

if 'nature' not in st.session_state:
    st.session_state.nature = '高冷傲娇心里一直默默暗恋用户，却由于害羞从未开口言明'

#侧边栏制作

with st.sidebar:
    st.subheader("AI智能伴侣")
    # 昵称输入框
    nick_name = st.text_input('昵称',placeholder = '请输入昵称',value = st.session_state.nick_name)
    if nick_name:
        st.session_state.nick_name = nick_name
    # 性格输入框
    nature = st.text_area('性格',placeholder = '请输入性格',value = st.session_state.nature)
    if nature:
        st.session_state.nature = nature



#初始化聊天信息

if 'message' not in st.session_state:
    st.session_state.message = []


#展示聊天信息

for message in st.session_state.message:
    st.chat_message(message["role"]).write(message["content"])

#系统提示词

system_prompt = """
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
"""  # 在这里提供AI的角色定位
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
             "content": system_prompt % (st.session_state.nick_name, st.session_state.nature)},
            *st.session_state.message  #这样就成功让AI记住了我们的对话
        ],
        stream=True,
        reasoning_effort="high",
        extra_body={"thinking": {"type": "enabled"}}
    )
    #输出大模型返回的结果

    #非流式输出的代码

    # print('大模型返回的结果',response.choices[0].message.content)
    # st.chat_message('assistant').write(response.choices[0].message.content)

    #流式输出的代码

    response_message = st.empty() #创建一个新的组件，用于显示AI的返回结果
    full_response = ''
    for chunk in response:
        if chunk.choices[0].delta.content is not None:
            content = chunk.choices[0].delta.content
            full_response += content
            response_message.chat_message('assistant').write(full_response)
    st.session_state.message.append({"role": "assistant", "content": full_response})  # 保存AI返回的信息