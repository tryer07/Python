#案例1

#目标：根据提供的班级学生选课情况完成需求
#需求1：找出同时选修法语和艺术的学生
#需求2：找出同时选修四门课的学生
#需求3：找出选修了足球但没有选修篮球的学生
#需求4：统计每一个学生选修的课程数量

#班级学生选课情况如下：
#选修足球学生名单：

football_set = {'张三','李四','王五','徐立国','王娇','王林','王卓'}

#选修篮球学生名单：

basketball_set = {'张三','李四','王卓','徐立','张聪','林雪'}

#选修法语学生名单：

french_set = {'徐立','张聪','王五','王娇','林雪','徐立国','张三','刘佳'}

#选修艺术学生名单：

art_set = {'张三','王五','王娇','李四','林雪','徐立','张聪'}

#1.找出同时选修法语和艺术的学生名单

print(french_set.intersection(art_set))

#2.找出同时选修四门课的学生名单

print(football_set.intersection(basketball_set).intersection(french_set).intersection(art_set))

#3.找出选修了足球但没有选修篮球的学生名单
#思路一：

fb_set = football_set.difference(basketball_set)
print(f'选修了足球但没选修篮球的学生：{fb_set}')

#思路二：

fb_set1 = football_set - basketball_set
print(f'选修了足球但没选修篮球的学生：{fb_set1}')

#思路三：
#利用集合推导式

fb_set2 = {s for s in football_set if s not in basketball_set }
print(f'选修了足球但没选修篮球的学生：{fb_set2}')

# 4.统计每个学生的选课数量，并显示具体课程
# (1) 获取所有学生
all_set = football_set | basketball_set | french_set | art_set

# (2) 遍历每个学生，判断其选修了哪些课
print("\n学生选课情况明细：")
for student in all_set:
    courses = []
    if student in football_set:
        courses.append('足球')
    if student in basketball_set:
        courses.append('篮球')
    if student in french_set:
        courses.append('法语')
    if student in art_set:
        courses.append('艺术')
    # 输出姓名、课程数量和课程列表
    print(f'{student} 选修了 {len(courses)} 门课程：{"、".join(courses)}')
