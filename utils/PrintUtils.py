from colorama import Fore,Style
import sys


THOUGHT_COLOR = Fore.GREEN
OBSERVATION_COLOR = Fore.YELLOW
ROUND_COLOR = Fore.BLUE
CODE_COLOR = Fore.WHITE

def color_print(text, color=None, end="\n"):
    """
    使用彩色输出文本到控制台
    
    参数:
        text (str): 要输出的文本内容
        color (colorama.Fore): 文本颜色，使用colorama.Fore中定义的颜色常量
        end (str): 输出结束符，默认为换行符
        
    功能:
        1. 根据指定的颜色输出文本
        2. 处理编码错误的异常情况
        3. 支持自定义输出结束符
    """
    # 如果指定了颜色，添加颜色标记和重置样式
    if color is not None:
        content = color + text + Style.RESET_ALL + end
    else:
        content = text + end
    
    try:
        # 使用sys.stdout直接写入并刷新缓冲区
        sys.stdout.write(content)
        sys.stdout.flush()
    except UnicodeEncodeError:
        print("Encoding error")