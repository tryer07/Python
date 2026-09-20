#下面的写法保证了当文件操作完成后文件一定会被关闭，即使在操作过程中发生异常文件也会被关闭，推荐使用try...finally结构。

#1.打开文件

f = open('resources/资源释放', 'w', encoding ='utf-8')

try:
    #写入文件内容
    f.write('Hello, World!')


finally:
    #关闭文件
    f.close()
    print('文件已关闭')
