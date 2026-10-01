#使用Python的tkinter库来创建一个图形界面，并在其中绘制一个由红色线条组成的螺旋形图案

# 导入tkinter库和math数学库

from tkinter import *
import math

#创建一个Canvas组件，用于绘制图形，并设置其大小为400x400像素，背景为白色

canvas = Canvas(width=400, height=400, bg='white')

#使用pack布局管理器将Canvas组件添加到窗口中，并设置其扩展属性和填充属性以便填满整个窗口

canvas.pack(expand=True, fill=BOTH)

#设置螺旋的中心点坐标

center_x, center_y = 200, 200

#设置螺旋的圈数和起始角度

num_turns = 6
start_angle = 0

#绘制螺旋形线条，通过计算每个点的坐标来形成螺旋曲线

points = []

for i in range(360 * num_turns):
    angle = math.radians(i + start_angle)
    radius = i * 0.15
    x = center_x + radius * math.cos(angle)
    y = center_y + radius * math.sin(angle)
    points.append(x)
    points.append(y)

#使用create_line方法绘制螺旋线，设置线条颜色为红色，宽度为2

canvas.create_line(*points, fill='red', width=2, smooth=True)

#进入tkinter的主事件循环，等待用户交互

mainloop()
