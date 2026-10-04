#使用Python的tkinter库来创建一个图形界面，并在其中绘制一个由矩形组成的螺旋形图案

#导入tkinter模块

from tkinter import *

#创建一个Canvas组件，用于绘制图形，并设置宽高度均为400像素，背景颜色为白色

canvas = Canvas(width = 400,height = 400,bg = 'white')

#使用pack布局管理器将Canvas组件添加到窗口中，并设置其扩展属性和填充属性便于填满整个窗口

canvas.pack(expand = True,fill = BOTH)

#绘制19个矩形，形成螺旋图案

for i in range(19):

    #使用create_rectangle方法绘制矩形

    canvas.create_rectangle(i*20,i*20,400-i*20,400-i*20)

mainloop()
