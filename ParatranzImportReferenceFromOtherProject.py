from concurrent.futures import ThreadPoolExecutor

import requests, json

API_Tokens = ''  # 这是你在Paratranz的API Token
rwAPI = 'https://paratranz.cn/api/projects/{0}/terms'
inputProjectID = 3489  # 远行星号本体汉化项目的ID
outputProjectID = []  # 其他需要依赖借鉴的远行星号mod项目的ID
threadPool = ThreadPoolExecutor(max_workers=1)

HTTP_Header = {'Authorization': API_Tokens}

tInput = requests.get(rwAPI.format(inputProjectID), headers=HTTP_Header,
                      params={'page': '1', 'pageSize': '114514'}).json()

termData = []
for dictUnit in tInput['results']:
    termData.append({'term': dictUnit['term'], 'pos': dictUnit['pos'], 'note': dictUnit['note'],
                     'translation': dictUnit['translation'], 'variants': dictUnit['variants']})

for outID in outputProjectID:
    threadPool.submit(requests.put, **dict(url=rwAPI.format(outID), headers=HTTP_Header,
                                           files={'file': ('1.json', json.dumps(termData))}))

threadPool.shutdown()
