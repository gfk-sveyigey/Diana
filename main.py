import ctypes
import sys

from app.diana import Diana


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()  # 判断是否以管理员身份运行
    except:
        return False

if is_admin():
    diana = Diana()
    diana.start()
else:
    ctypes.windll.shell32.ShellExecuteW(None, 'runas', sys.executable, __file__, None, 1)

