import json

#写入json数据文件

# user = {
#     "name": "张三",
#     "age": 18,
#     "gender": "男",
#     "hobbies": ["Python"]
# }

# with open('resources/user.json','w',encoding = 'utf-8') as f:
    #ensure_ascii = False 代码作用：确保中文不被转义(默认为True，非ascii字符会被转义，改成False则不会)
    # indent = 4 代码作用：确保格式化
    # json.dump(user,f,ensure_ascii = False,indent = 4)

#读取json数据文件

with open('resources/user.json','r',encoding = 'utf-8') as f:
    user = json.load(f)
    print(user)
    print(type(user))
