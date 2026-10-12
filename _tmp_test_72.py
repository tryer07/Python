# 临时冒烟测试：验证重构后的 72 题结构
import importlib.util

spec = importlib.util.spec_from_file_location(
    'grade_system', r'D:\Python\Python项目存放点\Python练习题（100道）\72.简单版学生成绩管理系统.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

m = mod.StudentGradeManager()
assert m.add_student('张三') is True
assert m.add_student('张三') is False
assert m.add_grade('张三', 85) is True
assert m.add_grade('张三', 92.5) is True
assert m.add_grade('李四', 60) is False      # 学生不存在

assert m.show_average('张三') is True         # 正常打印平均分 88.75
assert m.show_average('李四') is False        # 查无此人

m.add_student('王五')
assert m.show_average('王五') is False        # 存在但无成绩

s = mod.Student('赵六')
assert s.calculate_average() == 0.0           # 无成绩恒返回 0.0（float）
s.add_grade(70)
assert abs(s.calculate_average() - 70.0) < 1e-9
m.show_all()

print('全部冒烟测试通过 ✔')
