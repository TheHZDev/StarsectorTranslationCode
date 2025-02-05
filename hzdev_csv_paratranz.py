import json
import os
import pprint
from csv import DictWriter, DictReader
from pathlib import Path
from typing import NamedTuple, List, Dict

from dataModel import ParatranzDataUnit

# 本脚本被设计为仅处理特定路径的文件，因此不会有探测行为。
# 汉化组的翻译检测将被直接舍弃，因为用不到。

PROJECT_DIRECTORY = Path(__file__).parent.parent
ORIGINAL_PATH = str(PROJECT_DIRECTORY / 'original')
TRANSLATION_PATH = str(PROJECT_DIRECTORY / 'localization')
PARA_TRANZ_PATH = str(PROJECT_DIRECTORY / 'para_tranz' / 'output')


class SingleFileConfig(NamedTuple):
    relativeFilePath: str  # 文件的相对路径
    columnIDName: str | tuple  # 索引列的列名
    columnTextNames: List[str]  # 要导出的文本列的列名

    @property
    def fileName(self) -> str:
        """文件名。"""
        return self.relativeFilePath.rpartition('/')[-1]

    @property
    def absoluteOriginalPath(self) -> str:
        """源文件的绝对路径。"""
        return os.path.join(ORIGINAL_PATH, self.relativeFilePath.replace('/', os.sep))

    @property
    def absoluteLocalizationPath(self) -> str:
        """目标文件的绝对路径。"""
        return os.path.join(TRANSLATION_PATH, self.relativeFilePath.replace('/', os.sep))

    @property
    def absoluteParatranzFilePath(self) -> str:
        """中间文件的绝对路径。"""
        return os.path.join(PARA_TRANZ_PATH, self.relativeFilePath.replace('/', os.sep)[:-4] + '.json')

    def makeFolders(self, *, folderLocalization: bool = False, folderParatranz: bool = False):
        """
        预先创建文件夹。确保写入的时候不会出错。

        :param folderLocalization: 创建目标文件的目录。
        :param folderParatranz: 创建中间文件的目录。
        """
        if folderLocalization:
            os.makedirs(self.absoluteLocalizationPath.rpartition(os.sep)[0], exist_ok=True)
        if folderParatranz:
            os.makedirs(self.absoluteParatranzFilePath.rpartition(os.sep)[0], exist_ok=True)


class csvSubParatranz:
    # 存储了各个CSV文件的对应路径，到时候直接遍历。
    __const_preFileConfig: List[SingleFileConfig]
    __const_errorsFile = 'surrogateescape'  # 指定默认错误处理方式

    def __init__(self):
        self.__const_preFileConfig = [
            # 原版
            SingleFileConfig('data/campaign/abilities.csv', 'id', ['name', 'desc']),
            SingleFileConfig('data/campaign/commodities.csv', 'id', ['name']),
            SingleFileConfig('data/campaign/industries.csv', 'id', ['name', 'desc']),
            SingleFileConfig('data/campaign/market_conditions.csv', 'id', ['name', 'desc']),
            SingleFileConfig('data/campaign/rules.csv', 'id', ['script', 'text', 'options']),
            SingleFileConfig('data/campaign/special_items.csv', 'id', ['name', 'desc', 'tech/manufacturer']),
            SingleFileConfig('data/campaign/submarkets.csv', 'id', ['name', 'desc']),
            SingleFileConfig('data/characters/skills/skill_data.csv', 'id', ['name', 'description']),
            SingleFileConfig('data/hulls/ship_data.csv', 'id', ['name', 'designation', 'tech/manufacturer']),
            SingleFileConfig('data/hulls/wing_data.csv', 'id', ['role desc']),
            SingleFileConfig('data/hullmods/hull_mods.csv', 'id',
                             ['name', 'tech/manufacturer', 'uiTags', 'desc', 'short', 'sModDesc']),
            SingleFileConfig('data/strings/descriptions.csv', ('id', 'type'),
                             ['text1', 'text2', 'text3', 'text4']),
            SingleFileConfig('data/shipsystems/ship_systems.csv', 'id', ['name']),
            SingleFileConfig('data/weapons/weapon_data.csv', 'id',
                             ['name', 'tech/manufacturer', 'primaryRoleStr', 'speedStr', 'trackingStr', 'turnRateStr',
                              'accuracyStr', 'customPrimary', 'customPrimaryHL', 'customAncillary',
                              'customAncillaryHL']),
            # 首次出现于工业革命mod之中，宠物相关数据
            SingleFileConfig('data/campaign/pets.csv', 'id', ['name', 'desc', 'natural_death']),
            # 首次出现于mod (AoTD - 尘世浮生)
            SingleFileConfig('data/campaign/aotd_colony_events.csv', 'eventId', ['name', 'options']),
            # 首次出现于 RAT mod中
            SingleFileConfig('data/campaign/rat_artifacts.csv', 'id', ['name']),
            SingleFileConfig('data/campaign/frontiers/rat_frontiers_facilities.csv', 'id', ['name', 'shortDesc']),
            SingleFileConfig('data/campaign/frontiers/rat_frontiers_modifers.csv', 'id', ['name', 'desc']),
            # 首次出现于势力争霸mod的0.11.1里，角色背景
            SingleFileConfig('data/config/exerelin/character_backgrounds.csv', 'id', ['name', 'shortDescription', 'longDescription']),
            # 推测是 mod (人之领余烬[AoTD] - 问道圣殿) 2.X 版本的内容，但首次出现于TASC mod中
            SingleFileConfig('data/campaign/aotd_tech_options.csv', 'id', ['name', 'rewards']),
            # 首次出现于TASC mod中，一些奇怪的提示信息
            SingleFileConfig('data/campaign/terraforming/aotd_integration/terraforming_requirements_OR.csv', 'id',
                             ['tooltip', 'tooltip_highlights']),
            # 首次出现于TASC mod，需要汉化的是工业设施名称
            SingleFileConfig('data/campaign/terraforming/industry_options.csv', 'id', ['tooltip']),
            # 首次出现于TASC mod，描述行星类型ID和数据
            SingleFileConfig('data/campaign/terraforming/planet_types.csv', ('id', 'terraforming_type_id'), ['name']),
            # 首次出现于TASC mod，项目名称和提示
            SingleFileConfig('data/campaign/terraforming/terraforming_projects.csv', 'id',
                             ['tooltip', 'tooltip_highlights', 'intel_complete_message', 'incomplete_message',
                              'incomplete_message_highlights', 'disrupted_message', 'disrupted_message_highlights']),
            # 首次出现于TASC mod
            SingleFileConfig('data/campaign/terraforming/terraforming_requirements_OR.csv', 'id',
                             ['tooltip', 'tooltip_highlights']),
            # 推测是MagicLib的成就系统的相关数据
            SingleFileConfig('data/config/magic_achievements.csv', 'id', ['name', 'description', 'tooltip']),
            # 首次出现于 SecondInCommand mod 中
            SingleFileConfig('data/config/secondInCommand/SCAptitudes.csv', 'id', ['name']),
            SingleFileConfig('data/config/secondInCommand/SCSkills.csv', 'id', ['name']),
            # 推测是VaryaSector所提供的HVB框架文件。看起来MagicLib也能试着兼容它
            SingleFileConfig('data/config/vayraBounties/unique_bounty_data.csv', 'bounty_id',
                             ['fleetName', 'flagshipName', 'greetingText', 'intelText']),
            # 首次出现于 AoTD - Question of Loyalty 中，各种势力的雇佣数据
            SingleFileConfig('data/campaign/aotd_rank_data.csv', 'rank_id', ['name', 'description']),
        ]

    @classmethod
    def OriginalToParatranz(cls):
        """处理翻译文件，写入中间文件，并显示日志消息。"""
        cls().__startWork(True)

    @classmethod
    def ParatranzToLocalization(cls):
        """处理中间文件，回写数据，并显示消息。"""
        cls().__startWork(False)

    def __startWork(self, isExtract: bool = False):
        for configUnit in self.__const_preFileConfig:
            if isExtract:
                self.__commonFromCSV(configUnit)
            else:
                self.__commonToCSV(configUnit)

    def __commonFromCSV(self, config: SingleFileConfig):
        """
        从给定的 csv 源文件中根据配置文件提取指定的内容，并输出到中间文件。

        :param config: 配置选项组。
        """
        if not os.path.isfile(config.absoluteOriginalPath):
            return
        tOriginal = self.__loadCSVFile(config.absoluteOriginalPath)
        result = []
        usedID = set()
        firstHeaderName = list(tOriginal[0].keys())[0]  # 第一个表头，如果以 `#` 开头，则该行被视为注释
        # 开始处理表格
        for csvLineNum in range(len(tOriginal)):
            realCSVLineNum = csvLineNum + 1
            lineUnit = tOriginal[csvLineNum]
            # 行注释检测
            if lineUnit[firstHeaderName] is None or lineUnit[firstHeaderName].strip().startswith('#'):
                continue
            # ID预处理
            if isinstance(config.columnIDName, str):
                tVar = lineUnit.get(config.columnIDName)
                if tVar is None or tVar.strip() == '':
                    continue
                elif tVar in usedID:
                    raise RuntimeError(f'警告：在 {config.absoluteOriginalPath} 中发现了 ID 相同的行！重复ID为 {tVar}，'
                                       f'在第 {realCSVLineNum} 行！')
                usedID.add(tVar)
                preRowID = f'{config.fileName}#{tVar}$'
            else:
                tVar = [lineUnit.get(subIDName) for subIDName in config.columnIDName]
                if any([unit is None or unit.strip() == '' for unit in tVar]):
                    continue
                elif str(tuple(tVar)) in usedID:
                    raise RuntimeError(
                        f'警告：在 {config.absoluteOriginalPath} 中发现了 ID 相同的行！重复ID为 {tuple(tVar)}，'
                        f'在第 {realCSVLineNum} 行！')
                usedID.add(str(tuple(tVar)))
                preRowID = f'{config.fileName}#{tuple(tVar)}$'
            # 处理文本行
            contextText = f'{config.fileName}第{str(realCSVLineNum).zfill(4)}行\n[本行原始数据]\n{pprint.pformat(lineUnit, sort_dicts=False)}'  # 上下文预处理
            for textColumnName in config.columnTextNames:
                # 键值需存在于文件中，键值对应的文本不能是None且不得为空
                if textColumnName in lineUnit and lineUnit.get(textColumnName) is not None and \
                        lineUnit.get(textColumnName).strip() != '':
                    tVar = ParatranzDataUnit(preRowID + textColumnName, lineUnit[textColumnName], contextText)
                    if config.fileName == 'rules.csv' and textColumnName == 'script' and '\"' not in lineUnit[
                        textColumnName]:
                        # 沿袭汉化组对于 script 列的处理规则
                        tVar.stage = 1
                    result.append(tVar.asDict())
        # 写入中间文件
        if len(result) > 0:
            print(f'从 {config.relativeFilePath} 文件中加载了 {len(result)} 条原文数据。')
            config.makeFolders(folderParatranz=True)
            with open(config.absoluteParatranzFilePath, 'w', encoding='utf-8') as tFile:
                json.dump(result, tFile, ensure_ascii=False, indent=4)

    def __commonToCSV(self, config: SingleFileConfig):
        """
        从给定的 csv 源文件中提取原始内容，使用中间文件的参数覆盖数据，最后整合输出到目标文件。

        :param config: 配置选项组。
        """
        if not os.path.isfile(config.absoluteOriginalPath) or not os.path.isfile(config.absoluteParatranzFilePath):
            return
        tOriginal = self.__loadCSVFile(config.absoluteOriginalPath)
        tParatranz = self.__loadParatranzJSON(config.absoluteParatranzFilePath)
        print(f'已加载 {config.relativeFilePath} 的 {len(tParatranz)} 条译文数据。')
        firstHeaderName = list(tOriginal[0].keys())[0]  # 第一个表头，如果以 `#` 开头，则该行被视为注释
        keyIndexCache = {}
        # 先给tOriginal上个索引，然后再慢慢找
        for csvLineNum in range(len(tOriginal)):
            lineUnit = tOriginal[csvLineNum]
            # 行注释检测
            if lineUnit[firstHeaderName] is None or lineUnit[firstHeaderName].strip().startswith('#'):
                continue
            # ID预处理
            if isinstance(config.columnIDName, str):
                tVar = lineUnit.get(config.columnIDName)
                if tVar is None or tVar.strip() == '':
                    continue
                preRowID = f'{config.fileName}#{tVar}'
            else:
                tVar = [lineUnit.get(subIDName) for subIDName in config.columnIDName]
                if any([unit is None or unit.strip() == '' for unit in tVar]):
                    continue
                preRowID = f'{config.fileName}#{tuple(tVar)}'
            keyIndexCache[preRowID] = csvLineNum
        # 遍历Paratranz数据
        for paratranzUnit in tParatranz:
            if paratranzUnit.isTranslated and paratranzUnit.translation != '':
                rowNum = keyIndexCache.get(paratranzUnit.key.rpartition('$')[0])
                if rowNum is None:
                    continue
                textColumnName = paratranzUnit.key.rpartition('$')[2]
                if textColumnName in tOriginal[rowNum]:
                    tOriginal[rowNum][textColumnName] = paratranzUnit.translation.replace(
                        '\\n', '\n').replace('^n', '\\n')
        # 写回目标文件
        config.makeFolders(folderLocalization=True)
        with open(config.absoluteLocalizationPath, 'w', encoding='utf-8', newline='',
                  errors=self.__const_errorsFile) as tFile:
            tWriter = DictWriter(tFile, list(tOriginal[0].keys()))
            tWriter.writeheader()
            tWriter.writerows(tOriginal)
        print(f'译文数据已整合至 {config.absoluteLocalizationPath} 中。')

    def __loadCSVFile(self, filePath: str) -> List[Dict[str, str | None]]:
        with open(filePath, 'r', encoding='utf-8', errors=self.__const_errorsFile) as tFile:
            csv_lines = [self.replace_weird_chars(l).replace('\\n', '^n') for l in tFile]
            return list(DictReader(csv_lines))

    @staticmethod
    def __loadParatranzJSON(filePath: str) -> List[ParatranzDataUnit]:
        result = []
        with open(filePath, 'rb') as tFile:
            for lineDict in json.load(tFile):
                result.append(ParatranzDataUnit(**lineDict))
        return result

    @staticmethod
    def replace_weird_chars(s: str) -> str:
        """
        来自前汉化组代码，确认没有被污染后引入。

        来自之前程序的注释：“由于游戏原文文件中可能存在以Windows-1252格式编码的字符（如前后双引号等），所以需要进行转换”

        :param s: 参数字符串。
        :return: 被处理过的字符串。
        """
        return s.replace('\udc94', '""') \
            .replace('\udc93', '""') \
            .replace('\udc92', "'") \
            .replace('\udc91', "'") \
            .replace('\udc96', "-") \
            .replace('\udc85', '...')

#     @classmethod
#     def test(cls):
#         print(cls().__loadCSVFile(r'D:\PycharmProjects\StarsectorTranslationCode\1.csv')[1])
#
# if __name__ == '__main__':
#     csvSubParatranz.test()
