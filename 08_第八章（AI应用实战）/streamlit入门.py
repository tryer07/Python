from pathlib import Path

# 获取当前代码文件（streamlit入门.py）所在的文件夹路径
BASE_DIR = Path(__file__).parent

# 定义一个辅助函数，专门用来拼接资源路径
def get_resource_path(filename):
    return str(BASE_DIR / 'resources' / filename)

#引入streamlit

import streamlit as st

#怎么进入网页，在控制台最稳妥的输入格式：streamlit run ".\08_第八章（AI应用实战）\streamlit入门.py"

#大标题

st.title('Streamlit 入门程序尝试')

st.title('Streamlit 一级标题')

st.title('Streamlit 二级标题')

#所构建网页的链接：http://localhost:8501/

#logo

st.logo(get_resource_path('作品页_12-2-1_楼体发光招牌.png'))

#段落文字

st.write('\n')
st.write('下面是一段文字展示：')
st.write('\n')
st.write('\n')
st.write('\n')
st.write('欢迎来到由外收内放制作的网页~')
st.write('这是我制作的第一个网页，')
st.write('当我看见它成功生成并呈现在我眼前的时候，')
st.write('我倍感激动。')
st.write('因为在以前我认为生成并设计一个网页十分地困难，')
st.write('没想到自己也有成功做到的一天。')
st.write('感谢自己一直坚持学习Python的知识到现在，')
st.write('希望自己可以继续加油！')
st.write('冲冲冲 ! !')
st.write('\n')
st.write('\n')
st.write('\n')

#图片

st.write('下面展示一些我自己比较喜欢的图片：')
st.image(get_resource_path('单车少年 (1).png'))
st.image(get_resource_path('地铁站的女孩.png'))
st.image(get_resource_path('少女心事2.png'))
st.write('\n')
st.write('\n')
st.write('\n')

#音频

st.write('下面是一段六级真题的听力~')
st.audio(get_resource_path('2025年6月六级音频1.MP3'))
st.write('\n')
st.write('\n')
st.write('\n')

#视频

#视频也是一样的方法，但是这里没有下载什么视频，因此暂时不放

#表格

st.write('下面是表格的输出：')
students_data = {
    '姓名':['张三','李四','王林','徐立'],
    '学号':['001','002','003','004'],
    '高考成绩':[554,557,671,432]
}
st.table(students_data)

#输入框

name = st.text_input('请输入您的名称~')

st.write(f'您输入的名称为：{name}')

#密码输入框

password = st.text_input('请输入您的名称~',type = 'password')

st.write(f'您输入的密码为：{password}，请记好哦~')

#单选按钮

gender = st.radio('请选择您的性别：',['male','female','unknown'],index=0)

st.write(f'您当前选择的性别为{gender}')
