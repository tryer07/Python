#案例1：根据提供的成绩单完成需求

#需求：
#1.计算每个学生的总分和各科平均分后一并输出
#2.统计每科的最高最低分和平均分后一并输出
#3.查找各科成绩高于90分的学生后输出

#成绩单如下：
# 001 张三    语文 = 85 数学 = 92 英语 = 78
# 002 李四    语文 = 92 数学 = 88 英语 = 95
# 003 王五    语文 = 78 数学 = 85 英语 = 82
# 004 王林    语文 = 99 数学 = 98 英语 = 87
# 005 十三    语文 = 96 数学 = 63 英语 = 100
# 006 曾铁    语文 = 61 数学 = 91 英语 = 93
# 007 王卓    语文 = 55 数学 = 17 英语 = 100
# 008 曾牛    语文 = 39 数学 = 99 英语 = 67
# 009 许木    语文 = 69 数学 =63  英语 = 66
# 010 周然    语文 = 57数学 = 8   英语 = 100

students = (
    ('001', '张三', 85, 92, 78),
    ('002', '李四', 92, 88, 95),
    ('003', '王五', 78, 85, 82),
    ('004', '王林', 99, 98, 87),
    ('005', '十三', 96, 63, 100),
    ('006', '曾铁', 61, 91, 93),
    ('007', '王卓', 55, 17, 100),
    ('008', '曾牛', 39, 99, 67),
    ('009', '许木', 69, 63, 66),
    ('010', '周然', 57, 8, 100)
)

#1.计算每个学生的总分和各科平均分后一并输出

for s in students:
    total = s[2] + s[3] + s[4]
    avg = total / 3
    print(f'学号:{s[0]} 姓名:{s[1]} 各科成绩: 语文 = {s[2]} 数学 = {s[3]} 英语 = {s[4]} 总分 = {total} 平均分 = {avg:.1f}')

#2.统计每科的最高最低分和平均分后一并输出

Chinese_scores = [s[2] for s in students]
Math_scores    = [s[3] for s in students]
English_scores = [s[4] for s in students]

print(f'语文最高分：{max(Chinese_scores)}\t语文最低分：{min(Chinese_scores)}\t语文平均分{sum(Chinese_scores)/len(Chinese_scores)}')

print(f'数学最高分：{max(Math_scores)}    数学最低分：{min(Math_scores)}     数学平均分{sum(Math_scores)/len(Math_scores)}')

print(f'英语最高分：{max(English_scores)}\t英语最低分：{min(English_scores)}\t英语平均分{sum(English_scores)/len(English_scores)}')

#3.查找平均成绩高于90分的学生后输出

for s in students:
    total = s[2] + s[3] + s[4]
    avg = total / 3
    if avg > 90:
        print('光荣榜(各科平均分大于90)：')
        print(f'学号:{s[0]} 姓名:{s[1]} 各科成绩: 语文 = {s[2]} 数学 = {s[3]} 英语 = {s[4]} 总分 = {total} 平均分 = {avg:.1f}')
