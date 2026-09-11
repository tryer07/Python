#字符串基本操作

# s = 'Hello!Python'
# print(s[0])
# print(s[-12])

#需要注意的是，字符串中的元素不支持修改
#s[3] = 'X'
#print(s[3])
#这样的代码是会报错的

# for i in s:
#     print(i)

#切片(步长正数从左往右，步长负数从右往左)

# print(s[:6:1]) #截取Hello！字符串
# print(s[6:13:1]) #截取Python字符串

s = '  Hello-World-Nice-to-meet-you!  '

#find() 查找该字符串第一次出现的位置
index = s.find('e')
print(index)

#count() 查找该字符串出现的次数
c = s.count('e')
print(c)

#upper() 将字符串转为大写
su = s.upper()
print(su)

#lower() 将字符串转为小写
sl = s.lower()
print(sl)

#split 将字符串按照指定字符串切割成列表
slist = list(s)
print(slist)

#strip 去除字符串两端的空格
ss = s.strip()
print(ss)

#replace 替换字符串中的内容为指定内容
s.replace('-','_')
print(s)

#startswith 判断字符串是否以制定字符串开头(结尾返回布尔值)
print(s.startswith('Hello'))
print(s.endswith('World'))

#由于字符串不可变，因此最后经过一系列调整后最后输出的字符串仍然和一开始相同
print(s)

