#dict的基本操作(使用键值对存储数据，键不可重复但支持修改)

#定义

dict1 = {'张三':554, 'lucy':576,'jessika':499,'李四':610,'徐立国':660}
print(dict1)
print(type(dict1))
#如果key重复了，后面的值会把前面的值覆盖掉
#dict1 = {'张三':554, 'lucy':576,'Jessika':499,'李四':610,'张三':670}
#print(dict1)
#此时这样的代码输出张三的值会是670

#访问
print(dict1['张三'])

#字典的增删改查

#增加/修改
dict1['张三'] = 654
print(dict1)

#查询

#查询分支一:根据key获取value的两种思路
#方法一

print(dict1['张三'])

#方法二
print(dict1.get('张三'))

#查询分支二:获取dict中的信息

print(dict1.keys())
print(dict1.values())
print(dict1.items())

#删除
#方法一

score = dict1.pop('lucy')
print(score)
print(dict1)

#方法二
del dict1['jessika']
print(dict1)

#遍历字典
for item in dict1.items():
    print(item)