#lambda函数(由于lambda只能写单行表达式，因此仅适用于简单函数的编写)

#接下来的代码会展示一下命名函数(即普通的函数)和匿名函数(lambda)的区别

#需求一：打印分割线

#定义(命名函数)

# def out_line():
#     print('-----')

#调用(命名函数)

# out_line()
#以上是命名函数的定义

#定义(匿名函数)

out_line = lambda : print('-----')

#调用(匿名函数)

out_line()

#需求二：计算两个数的和

#定义(命名函数)

def add(x,y):
    return x + y

#调用(命名函数)

print(add(1,2))

#定义(匿名函数)

add = lambda a,b : a + b

#调用(匿名函数)

print(add(1,2))

#需求三：完成如下列表的排序操作，让每一个元素按照字符大小顺序从小到大排列

#思路一(原列表的排序方式)
#这样排序的思路是按照字母的顺序排列，并不符合要求

# data_list = ['C','C++','Python','Jack','PHP','Go','Javascript','Rust']
#
# data_list.sort()
#
# print(data_list)

#思路二(匿名函数思路)

#从小到大排列

# data_list = ['C','C++','Python','Jack','PHP','Go','Javascript','Rust']

# data_list.sort(key = lambda item: len(item))

# print(data_list)

#从大到小排列

data_list = ['C','C++','Python','Jack','PHP','Go','Javascript','Rust']

data_list.sort(key = lambda item: len(item) , reverse = True)

print(data_list)
