#请使用Python的tkinter库来创建一个界面，并在其中绘制一个由圆圈组成的螺旋形图案。

#引入模块

from tkinter import *

#创建一个Canvas组件，用于绘制图形，并设置其大小为400x400像素

canvas = Canvas(width=400,height=400,bg='white')

#使用pack布局管理器将Canvas组件添加到窗口中，并设置其扩展属性和填充属性便于填充整个窗口

canvas.pack(expand = True, fill = BOTH)

#绘制26个圆圈，螺旋形圆圈图案

for i in range(26):

    #使用create_oval并调整参数，绘制螺旋形圆圈图案

    canvas.create_oval(200-i*10,200-i*10,200+i*10,200+i*10)

canvas.mainloop()
