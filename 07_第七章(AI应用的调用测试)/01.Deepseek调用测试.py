import os
from openai import OpenAI

#创建与AI交互的大模型客户端对象(DEEPSEEK_API_KEY环境变量的名字，值就是DeepSeek的API_KEY的)

client = OpenAI(
    api_key=os.environ.get('DEEPSEEK_API_KEY'),
    base_url="https://api.deepseek.com")

#与AI大模型进行交互()

# noinspection bad-argument-type
response = client.chat.completions.create(
    model="deepseek-flash",
    messages=[
        {"role": "system", "content": "你是一名通识专家，通晓并精通所有的知识，会以严谨的逻辑和亲切的语气回答我的问题并给予充分的情绪价值"}, #在这里提供AI的角色定位
        {"role": "user", "content": "你是谁？你能帮我做什么"}, #在这里输入你要和AI说的内容
    ],
    stream=False,
    reasoning_effort="high",
    extra_body={"thinking": {"type": "enabled"}}
)

#输出大模型返回的结果

print(response.choices[0].message.content)