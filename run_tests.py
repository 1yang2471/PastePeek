"""使用当前 Python 环境运行全部测试。"""
import subprocess
import sys

# 使用独立 pytest 进程，避免嵌入式运行的收尾异常。
sys.exit(subprocess.call([sys.executable, "-m", "pytest", *sys.argv[1:]]))
