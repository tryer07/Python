#使用Python的tkinter库来创建一个图形界面，并在其中绘制一个由红色线条组成的螺旋形图案

# 导入tkinter库

from tkinter import *

#创建一个Canvas组件，用于绘制图形,并设置高度宽度和背景颜色

canvas = Canvas(width = 300,height = 300,bg = 'white')

#使用pack布局管理器将Canvas组件添加到窗口中，并设置其扩展属性和填充属性以便填满整个窗口

canvas.pack(expand = True,fill = BOTH)

#初始化第一组线条的起点坐标

x0 , y0 = 163,163

#初始化第一组线条的终点y坐标的偏移量

y1 = 175

#绘制第一组螺旋形线条

for i in range(19):

    #使用create_line方法绘制直线，其参数分别为起点坐标和终点坐标，以及线条的宽度和颜色

    canvas.create_line(x0,y0,x0,y1,width = 1,fill = 'red',smooth = True)

    #更新y0和y1的值，以便绘制下一条线，每次向左上方移动5个像素

    x0 , y0 = x0 - 5 , y0 - 5

    #更新终点y坐标的偏移量

    y1 += 5

#初始化第二组线条的起点坐标

# noinspection redeclaration
x0 , y0 = 163,163

#初始化第二组线条的终点y坐标的偏移量

y1 = 175

#绘制第二组螺旋形线条

for i in range(19):

    #使用create_line方法绘制直线，其参数分别为起点坐标和终点坐标，以及线条的宽度和颜色

    canvas.create_line(x0,y0,x0,y1,width = 1,fill = 'red',smooth = True)

    #更新y0和y1的值，以便绘制下一条线，每次向右上方移动5个像素

    x0 , y0 = x0 + 5 , y0 + 5

    #更新终点y坐标的偏移量

    y1 += 5

#进入tkinter的主事件循环，等待用户交互

mainloop()







