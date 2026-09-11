# type
# print(type('Hello'))
# print(type(True))
# print(type(False))
# print(type(None))
# print(type(10))
# print(type(3.1415926535))
# 以上输出均存在警告信息，但是可以正常运行

# isinstance
# num = 100
# print(isinstance(num,int))
# print(isinstance(num,float))
#
# 字符串
# a = 'Hello'
# b = "Hello world"
# c = """
# \t君不见黄河之水天上来
# \t奔流到海不复回
# \t人生得意须尽欢
# \t莫使金樽空对月
# """
# \t代表缩进
# print(a)
# print(b)
# print(c)
# d = '渡川赴月\n外收内放'
# print(d)

# 字符串拼接
# 尝试1
# a = '待到秋来九月八'
# b = '我花开后百花杀'
# c = '满城尽带黄金甲'
# d = '冲天香气透长安'
# print('一首喜欢的诗: ''\n'+ a + ',''\n' + b + ',''\n' + c + ',''\n' + d + '。')

# 尝试2
# name = '蔡徐坤'
# year = '两年半'
# hobby = '唱跳rap篮球'
# print('全民制作人们大家好：''我是练习时长' + year +'的个人偶像练习生'',' + name + ',''(露齿微笑ing)''喜欢' + hobby + ',''music(脱外套)''!')

# 占位符
#尝试1
name = '李华'
print('亲爱的%s,你最近过得怎么样？'% name)

#尝试2
name = '李华'
age = 18
print('我叫%s，今年%s岁。'%(name,age))

#尝试3
name = '蔡徐坤'
year = '两年半'
hobby = '唱跳rap篮球'
print(f'全民制作人们大家好，我是练习时长{year}的个人偶像练习生{name}，喜欢{hobby}，music~')