import requests
from concurrent.futures import ThreadPoolExecutor

API_Tokens = ''  # 这是你在Paratranz的API Token
rwAPI = 'https://paratranz.cn/api/projects/{0}/terms'
inputProjectID = 3489  # 远行星号本体汉化项目的ID
outputProjectID = []  # 其他需要依赖借鉴的远行星号mod项目的ID
threadPool = ThreadPoolExecutor(max_workers=len(outputProjectID) * 25)

HTTP_Header = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
    'Authorization': API_Tokens,
    'Accept': 'application/json, text/plain, */*'
}

tInput = requests.get(rwAPI.format(inputProjectID), headers=HTTP_Header,
                      params={'page': '1', 'pageSize': '1000'}).json()
for dictUnit in tInput['results']:
    newTerm = {'term': dictUnit['term'], 'pos': dictUnit['pos'], 'note': dictUnit['note'],
               'translation': dictUnit['translation'], 'variants': dictUnit['variants']}
    for outID in outputProjectID:
        threadPool.submit(requests.post, **dict(url=rwAPI.format(outID), headers=HTTP_Header, json=newTerm))

threadPool.shutdown()
