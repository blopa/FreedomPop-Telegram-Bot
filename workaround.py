import os
import sys


def main():
    pid = sys.argv[1]
    if pid:
        os.system('kill ' + pid)
        result = os.popen("ps -ef | grep " + pid + " | grep -v grep | awk '{print $2}'").read()
        if result == "":
            os.system('nohup python app.py FREEDOMPOP &')


if __name__ == '__main__':
    main()
