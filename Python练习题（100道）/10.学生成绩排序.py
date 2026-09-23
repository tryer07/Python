# 给定一个学生信息列表，根据学生的成绩进行排序

students = [
    {'snum': 101, 'sname': '张三', 'sgrade': 88},
    {'snum': 102, 'sname': '李四', 'sgrade': 79},
    {'snum': 103, 'sname': '王五', 'sgrade': 91},
    {'snum': 104, 'sname': '林芳', 'sgrade': 66},
]

# 根据学生成绩排序（使用匿名函数让字典也可以进行大小的比较从而排序）

# reverse=True 表示降序（从高到低）

students_sort = sorted(students, key=lambda x: x['sgrade'], reverse=True)

# 一行输出一个学生

print('学号\t姓名\t成绩')
print('-' * 25)
for s in students_sort:
    print(f"{s['snum']}\t{s['sname']}\t{s['sgrade']}")

