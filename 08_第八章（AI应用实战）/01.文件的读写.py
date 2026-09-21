#读文件

#1.打开文件

#  f = open('resources/Python文件调用测试.txt', 'r', encoding ='utf-8')

#2.读取文件内容

# content = f.read() #读取文件所有内容
# print(content)

# content_list = f.readlines() #读取文件所有内容并返回一个列表
# for line in content_list:
#     print(line.strip())

#3.关闭文件

# f.close()

# -------------------------------------------------------------------

# 写文件

# 1.创建文件

f = open('resources/静夜思.txt', 'w', encoding='utf-8')

# 2.写入文件内容

f.write('静夜思\n')
f.write('床前明月光\n')
f.write('疑是地上霜\n')
f.write('举头望明月\n')
f.write('低头思故乡\n')

# 3.关闭文件

f.close()