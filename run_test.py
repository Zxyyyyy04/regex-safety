# 仅用于本地开发测试的快捷入口
import sys
from regex_safety.cli import main


if __name__ == "__main__":
    # 模拟命令行参数
    sys.argv = ["cli.py", "(a+)+b"]
    sys.exit(main(sys.argv))