from concurrent.futures import ThreadPoolExecutor

import os.path
import requests

from hzdev_misc_paratranz import PARA_TRANZ_PATH

API_Tokens = ''  # 这是你在Paratranz的API Token
projectID = -1  # 这是你要同步文件的项目的ID

threadPool = ThreadPoolExecutor()

session = requests.Session()
session.headers['Authorization'] = API_Tokens

# 远程文件数据：文件ID、文件路径列表
existFileNames = {}
for unit in session.get(f'https://paratranz.cn/api/projects/{projectID}/files').json():
    existFileNames[os.path.join(PARA_TRANZ_PATH, *unit['name'].split('/'))] = unit['id']


def threadTask(filePath: str, uploadTask: bool, fileID: int = None):
    realFileName = filePath.split(os.sep)[-1]
    if uploadTask:
        uploadPath = filePath.split(PARA_TRANZ_PATH)[1].replace(realFileName, '')[1:-1].replace(os.sep, '/')
        session.post(f'https://paratranz.cn/api/projects/{projectID}/files', data={'path': uploadPath},
                     files={'file': (realFileName, open(filePath, 'rb'))})
        print(f'文件{realFileName}已上传。')
    else:
        session.post(f'https://paratranz.cn/api/projects/{projectID}/files/{fileID}',
                     files={'file': (realFileName, open(filePath, 'rb'))})
        print(f'文件{realFileName}已更新。')


# 遍历本地文件
for dirPath, _, fileNames in os.walk(PARA_TRANZ_PATH):
    for fileName in fileNames:
        realFilePath = os.path.join(dirPath, fileName)
        if realFilePath in existFileNames:
            # 更新文件
            threadPool.submit(threadTask, realFilePath, False, existFileNames[realFilePath])
        else:
            # 上传文件
            threadPool.submit(threadTask, realFilePath, True, None)

threadPool.shutdown()
