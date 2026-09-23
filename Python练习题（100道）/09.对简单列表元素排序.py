#给定一个简单列表，对其元素进行排序

#注意这里声明的简单列表指的是元素类型不是复合元素类型(如列表/元组/字典)

#正序

list1 = [10,30,20,50,40]

list1.sort()

print(list1)

#倒序

list2 = [100,310,200,250,90]

list2.sort(reverse = True)

print(list2)

#对列表排序(但不改变原列表顺序)

#语句：sorted(iterable,key = None,reverse = False)

#iterable:想要排序的可迭代对象

#key(可选传参)

#reverse(可选传参，选择布尔值True或者False)

list3 = sorted(list2)

print('原列表：',list2)
print('排序后的列表：',list3)