import csv
import json
import os.path
from typing import List

result_fileName = 'para_tranz_map.json'
const_refData = {
    'data/campaign/abilities.csv': {
        'id_column_name': 'id',
        'text_column_names': ['name', 'desc']
    },
    'data/campaign/commodities.csv': {
        'id_column_name': 'id',
        'text_column_names': ['name']
    },
    'data/campaign/industries.csv': {
        'id_column_name': 'id',
        'text_column_names': ['name', 'desc']
    },
    'data/campaign/market_conditions.csv': {
        'id_column_name': 'id',
        'text_column_names': ['name', 'desc']
    },
    'data/campaign/pets.csv': {  # 首次出现于工业革命mod之中
        'id_column_name': 'id',
        'text_column_names': ['name', 'desc', 'natural_death']
    },
    'data/campaign/rules.csv': {
        'id_column_name': 'id',
        'text_column_names': ['script', 'text', 'options']
    },
    'data/campaign/special_items.csv': {
        'id_column_name': 'id',
        'text_column_names': ['name', 'desc', 'tech/manufacturer']
    },
    'data/campaign/submarkets.csv': {
        'id_column_name': 'id',
        'text_column_names': ['name', 'desc']
    },
    'data/characters/skills/skill_data.csv': {
        'id_column_name': 'id',
        'text_column_names': ['name', 'description', 'author']
    },
    # 'data/hullmods/hull_mods.csv': {
    #     'id_column_name': 'id',
    #     'text_column_names': ['name', 'tech/manufacturer', 'uiTags', 'desc', 'short', 'sModDesc']
    # },
    'data/hulls/ship_data.csv': {
        'id_column_name': 'id',
        'text_column_names': ['name', 'designation', 'tech/manufacturer']
    },
    'data/hulls/wing_data.csv': {
        'id_column_name': 'id',
        'text_column_names': ['role desc']
    },
    'data/shipsystems/ship_systems.csv': {
        'id_column_name': 'id',
        'text_column_names': ['name']
    },
    'data/weapons/weapon_data.csv': {
        'id_column_name': 'id',
        'text_column_names': ['name', 'tech/manufacturer', 'primaryRoleStr', 'speedStr', 'trackingStr', 'turnRateStr',
                              'accuracyStr', 'customPrimary', 'customPrimaryHL', 'customAncillary', 'customAncillaryHL']
    },
    'data/campaign/aotd_colony_events.csv': {  # 首次出现于mod (AoTD - 尘世浮生)
        'id_column_name': 'eventId',
        'text_column_names': ['name', 'options']
    },
    'data/campaign/rat_artifacts.csv': {  # 首次出现于RandomAssortmentOfThings mod里
        'id_column_name': 'id',
        'text_column_names': ['name']
    },
    'data/config/exerelin/character_backgrounds.csv': {  # 首次出现于势力争霸mod的0.11.1里
        'id_column_name': 'id',
        'text_column_names': ['name', 'shortDescription']
    },
    'data/campaign/frontiers/rat_frontiers_facilities.csv': {  # 首次出现于RandomAssortmentOfThings mod里
        'id_column_name': 'id',
        'text_column_names': ['name', 'shortDesc']
    },
    'data/campaign/frontiers/rat_frontiers_modifers.csv': {  # 首次出现于RandomAssortmentOfThings mod里
        'id_column_name': 'id',
        'text_column_names': ['name', 'desc']
    },
    'data/campaign/aotd_tech_options.csv': {  # 推测是 mod (人之领余烬[AoTD] - 问道圣殿) 2.X 版本的内容，但首次出现于TASC mod中
        'id_column_name': 'id',
        'text_column_names': ['name', 'rewards', 'otherReq']  # 对rewards列的翻译也许需要谨慎处理
    },
    'data/campaign/terraforming/aotd_integration/terraforming_requirements_OR.csv': {  # 首次出现于TASC mod中，一些奇怪的提示信息
        'id_column_name': 'id',
        'text_column_names': ['tooltip', 'tooltip_highlights']
    },
    'data/campaign/terraforming/industry_options.csv': {  # 首次出现于TASC mod，需要汉化的是工业设施名称
        'id_column_name': 'id',
        'text_column_names': ['tooltip']
    },
    'data/campaign/terraforming/planet_types.csv': {  # 首次出现于TASC mod，描述行星类型ID和数据
        'id_column_name': ['id', 'terraforming_type_id'],
        'text_column_names': ['name']
    },
    'data/campaign/terraforming/project_effects.csv': {  # 首次出现于TASC mod，描述地貌改造项目的影响（大部分都是代码）
        'id_column_name': 'id',
        'text_column_names': ['data']
    },
    'data/campaign/terraforming/terraforming_projects.csv': {  # 首次出现于TASC mod，项目名称和提示
        'id_column_name': 'id',
        'text_column_names': ['tooltip', 'tooltip_highlights', 'intel_complete_message', 'incomplete_message',
                              'incomplete_message_highlights', 'disrupted_message', 'disrupted_message_highlights']
    },
    'data/campaign/terraforming/terraforming_requirements_OR.csv': {  # 首次出现于TASC mod
        'id_column_name': 'id',
        'text_column_names': ['tooltip', 'tooltip_highlights']
    },
    'data/config/secondInCommand/SCAptitudes.csv': {  # 首次出现于 Second-In-Command mod 中，推测是主领域分类
        'id_column_name': 'id',
        'text_column_names': ['name']
    },
    'data/config/secondInCommand/SCCategories.csv': {  # 首次出现于 Second-In-Command mod 中，推测是子领域（Aptitude的下级）
        'id_column_name': 'id',
        'text_column_names': ['name']
    },
    'data/config/secondInCommand/SCSkills.csv': {  # 首次出现于 Second-In-Command mod 中，推测是技能数据
        'id_column_name': 'id',
        'text_column_names': ['name']
    },
    'data/campaign/aotd_faction_behaviour.csv': {  # 首次出现于 问道圣殿 2.4.11，推测是携带数据库的舰队交易时的对话文本
        'id_column_name': 'factionId',
        'text_column_names': ['initResponse', 'dialogSelectOptionName', 'dialogDismayOptionName', 'responseAfter']
    },
    'data/campaign/aotd_production_projects.csv': {  # 首次出现于 问道圣殿 2.4.11，推测是特殊性工程项目数据
        'id_column_name': 'id',
        'text_column_names': ['name', 'projectDescription', 'stageNames', 'progressString', 'highlights']
    },
    'data/campaign/aotd_research_project.csv': {  # 首次出现于 问道圣殿 2.4.11，推测是特殊研究性项目数据
        'id_column_name': 'id',
        'text_column_names': ['name', 'stageMap', 'projectDescription']
    },
    # '': {
    #     'id_column_name': '',
    #     'text_column_names': []
    # },
    #
}


def makeConfigFile(rootFolderPath: str, allFiles: List[str], **kwargs):
    """
    通过匹配、查找和分析游戏的具体csv文件，来生成供汉化组程序使用的配置文件。

    :param rootFolderPath: Original的根目录。
    :param allFiles: 所有文件的相对路径。
    :param kwargs: 其他参数。
    """
    if 'exit' in kwargs:
        return
    result = []

    def getCSVHeader(filePath: str) -> List[str]:
        with open(os.path.join(rootFolderPath, filePath.replace('/', os.sep)), encoding='UTF-8') as tFile_csv:
            return list(csv.DictReader(tFile_csv))[0].keys()

    for unit in allFiles:
        if not unit.endswith('.csv'):
            continue
        filePathStr = unit[1:]
        # 其它处理流程
        if filePathStr == 'data/hullmods/hull_mods.csv':
            tVar = {'path': 'data/hullmods/hull_mods.csv', 'id_column_name': 'id',
                    'text_column_names': ['name', 'tech/manufacturer', 'uiTags', 'desc', 'short']}
            if 'sModDesc' in getCSVHeader(filePathStr):
                tVar['text_column_names'].append('sModDesc')
            result.append(tVar)
        elif filePathStr == 'data/strings/descriptions.csv':
            tVar = {'path': 'data/strings/descriptions.csv', 'id_column_name': ['id', 'type'], 'text_column_names': []}
            for subTitle in getCSVHeader(filePathStr):
                if len(subTitle.strip()) != '' and subTitle not in ('id', 'type', 'notes'):
                    tVar['text_column_names'].append(subTitle)
            result.append(tVar)
        # 一般处理流程
        elif filePathStr in const_refData:
            t2 = const_refData.get(filePathStr).copy()
            t2['path'] = filePathStr
            result.append(t2)

    with open(result_fileName, 'w', encoding='UTF-8') as tFile:
        json.dump(result, tFile)


def preStartConfirm() -> dict:
    """插入一段问话和判断并询问一些必要问题。"""
    result = {}
    if os.path.isfile(result_fileName):
        from datetime import datetime
        modifiedStr = datetime.fromtimestamp(os.stat(result_fileName).st_mtime).strftime('%Y年%m月%d日')
        userSelect = input(f'检测到配置文件已存在，其最近一次修改时间是{modifiedStr}，是否覆盖？(Y/n)')
        if userSelect.upper().strip() == 'N':
            result['exit'] = True
            print('将不会覆盖文件。')
    return result