#set的基本操作(无序，不可重复，不可修改)

#定义
# s = {'a','a','b','c','d','e','f','g','h','i'}

#空集合定义
#s1 = set{}这样的定义是字典
#由于集合无序，因此不支持下标索引访问

# s1 = set()
# print(s1)
# print(type(s1))
#补充：集合是自动去重的

#add() 添加元素

s = {88,188,288,388,488,588,688,788}
s.add(888)
print(s)

#remove() 移除集合中指定元素(元素不存在会报错)

s.remove(88)
print(s)

#pop() 随机删除集合中的元素并返回

a = s.pop()
print(a)
print(s)

#clear() 清空集合

s.clear()
print(s)

s1 = {'a','b','c'}
s2 = {'b','c','d'}

#difference() 求取两个集合的差集(第一个集合包含但第二个集合不包含的元素)

print(s1.difference(s2))
print(s2.difference(s1))

#union() 两个集合的并集

print(s1.union(s2))
print(s2.union(s1))

#intersection() 两个集合的交集

print(s2.intersection(s1))
