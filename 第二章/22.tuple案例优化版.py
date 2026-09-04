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

# ---------- 1. 每个学生总分和平均分 ----------
print("=" * 50)
print("学生个人成绩表")
print("=" * 50)
print(f"{'学号':<6}{'姓名':<6}{'语文':>6}{'数学':>6}{'英语':>6}{'总分':>6}{'平均分':>8}")
print("-" * 50)
for s in students:
    total = s[2] + s[3] + s[4]
    avg = total / 3
    print(f"{s[0]:<6}{s[1]:<6}{s[2]:>6}{s[3]:>6}{s[4]:>6}{total:>6}{avg:>8.1f}")

# ---------- 2. 各科统计 ----------
print("\n" + "=" * 50)
print("各科最高分、最低分、平均分")
print("=" * 50)
chinese = [s[2] for s in students]
math = [s[3] for s in students]
english = [s[4] for s in students]

print(f"语文  最高分: {max(chinese):>3}  最低分: {min(chinese):>3}  平均分: {sum(chinese)/len(chinese):>5.1f}")
print(f"数学  最高分: {max(math):>3}  最低分: {min(math):>3}  平均分: {sum(math)/len(math):>5.1f}")
print(f"英语  最高分: {max(english):>3}  最低分: {min(english):>3}  平均分: {sum(english)/len(english):>5.1f}")

# ---------- 3. 分层名单 ----------
# 先构建包含完整信息的列表
student_stats = []
for s in students:
    total = s[2] + s[3] + s[4]
    avg = total / 3
    student_stats.append((s[0], s[1], s[2], s[3], s[4], total, avg))

# 按平均分从高到低排序
student_stats.sort(key=lambda x: x[6], reverse=True)

# 定义打印函数，避免重复代码
def print_group(title, condition):
    print("\n" + "=" * 50)
    print(title)
    print("=" * 50)
    print(f"{'学号':<6}{'姓名':<6}{'语文':>6}{'数学':>6}{'英语':>6}{'总分':>6}{'平均分':>8}")
    print("-" * 50)
    for item in student_stats:
        if condition(item[6]):
            print(f"{item[0]:<6}{item[1]:<6}{item[2]:>6}{item[3]:>6}{item[4]:>6}{item[5]:>6}{item[6]:>8.1f}")

# 光荣榜：平均分 > 90
print_group("光荣榜（平均分 > 90）", lambda avg: avg > 90)

# 普通学生：60 < 平均分 <= 90
print_group("普通学生（60 < 平均分 ≤ 90）", lambda avg: 60 < avg <= 90)

# 重点关注：平均分 <= 60
print_group("重点关注学生（平均分 ≤ 60）", lambda avg: avg <= 60)