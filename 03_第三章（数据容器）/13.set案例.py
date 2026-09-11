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

#4.统计每个学生的选课数量
#(1). 获取学生名单

all_set = football_set | basketball_set | french_set | art_set
print(all_set)

#(2).获取每一个学生选修的课程数量

all_list = [*football_set,*basketball_set,*french_set,*art_set]
print(all_list)
for i in all_set:
    print(f'{i}选修了{all_list.count(i)}门课程')
