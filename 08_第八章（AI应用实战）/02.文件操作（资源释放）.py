#下面的写法保证了当文件操作完成后文件一定会被关闭，即使在操作过程中发生异常文件也会被关闭。

#方法一：使用try...finally结构(繁琐)

#1.打开文件

f = open('resources/资源释放', 'w', encoding ='utf-8')

try:
    #2.写入文件内容
    f.write('Hello, World!')


finally:
    #3.关闭文件
    f.close()
    print('文件已关闭')

# 方式二：使用with语句(更加推荐使用，因为它更简洁，且能自动处理文件的关闭。)
with open('resources/资源释放', 'w', encoding ='utf-8') as f:
    f.write('Hello, World!')
