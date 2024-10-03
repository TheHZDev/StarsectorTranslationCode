import pprint
from os import sep, scandir, DirEntry
from os.path import isfile, isdir
from typing import List, Dict, Tuple, NamedTuple
import re
import csv
from enum import Enum
from hashlib import md5

import json
import json5

from para_tranz_script import PARA_TRANZ_PATH, ORIGINAL_PATH, TRANSLATION_PATH

PARA_TRANZ_PATH = str(PARA_TRANZ_PATH)
ORIGINAL_PATH = str(ORIGINAL_PATH)
TRANSLATION_PATH = str(TRANSLATION_PATH)


class RegisterEnum(Enum):
    """
    此类用于实现注册分类器时的分类标签参考。本身无实际意义，仅作分类使用。

    标签后的字符串是注释，一般情况下请不要直接使用。
    """
    path: str = 'PathOnly'
    folder: str = 'FolderOnly'
    ext: str = 'ExtOnly'
    folder_ext: str = 'FolderPlusExt'
    # 特殊分类标签
    mission: str = 'MissionOnly'
    all: str = 'Everything'


class ParatrazProject:

    def __init__(self):
        """
        配置文件注册方法：
            关键字 "Register": str
                "mission" - 该程序集专一处理mission部分的文件。

                "path" - 程序集只处理指定的文件。

                "folder" - 该相对目录下所有的文件都交给程序集处理。

                "ext" - 程序集处理指定后缀的文件。

                "folder_ext" - 在该相对目录下且满足指定后缀的文件交给程序集处理。

                "all" - 程序集处理所有级别的文件。
            关键字 "Path": List[str]
                相对路径列表，相对路径需要以'/'开头。需要将"Register"指定为"path"。
            关键字 "Folder": List[str]
                相对路径列表，相对路径需要以'/'开头。需要将"Register"指定为"folder"。
            关键字 "Ext": List[str]
                后缀列表。需要将"Register"指定为"ext"。后缀开头不带'.'。
            关键字 "Folder_Ext": List[Tuple[str, str]]
                目录+后缀 列表，需要将"Register"指定为"folder_ext"。元组第一个值是相对路径（以'/'开头），第二个是后缀。
            关键字 "FromOriginal": str -> func(original原文文件路径，paratranz输出文件路径)
                将原文件写入Paratranz格式的翻译文件。
            关键字 "ToLocalization": str -> func(original原文文件路径，paratranz译文文件路径，localization目标文件路径)
                将翻译好的文件写回原文件。
            关键字 "FromMission": str -> func(descriptor.json原文文件路径，mission_text.txt原文文件路径，paratranz输出文件路径)
                仅当关键字为 "mission" 时有效，将descriptor.json和mission_text.txt内容合并并写入Paratranz格式的翻译文件。
            关键字 "ToMission": str -> func(descriptor.json原文文件路径，mission_text.txt原文文件路径，paratranz输出文件路径,descriptor.json译文文件路径，mission_text.txt译文文件路径)
                仅当关键字为 "mission" 时有效，将翻译好的文件写回原文件。
        """
        self.__originalFilePaths = self.__scanSpecialPath(ORIGINAL_PATH)  # 相对路径存储
        self.__paratranzOutputPaths = self.__scanSpecialPath(PARA_TRANZ_PATH)
        self.__localizationOutputPaths = self.__scanSpecialPath(TRANSLATION_PATH)
        self.__config: List[dict] = []
        self.ImportConfig()  # 注册配置文件
        self.__missionProgram = {}
        self.__pathProgram: List[dict] = []
        self.__extProgram: List[dict] = []
        self.__folderProgram: List[dict] = []
        self.__folder_ext_Program: List[dict] = []
        self.__allProgram: List[dict] = []
        self.__filterConfig()

    def ImportConfig(self):
        raise NotImplementedError

    def __filterConfig(self):
        for program in self.__config:
            if isinstance(program, dict) and program.get('Register') == RegisterEnum.mission and len(
                    self.__missionProgram) == 0:
                self.__missionProgram = program
            elif isinstance(program, dict) and 'FromOriginal' in program and 'ToLocalization' in program:
                tVar = program.get('Register')
                if tVar == RegisterEnum.path and isinstance(program.get('Path'), list):
                    self.__pathProgram.append(program)
                elif tVar == RegisterEnum.folder and isinstance(program.get('Folder'), list):
                    self.__folderProgram.append(program)
                elif tVar == RegisterEnum.ext and isinstance(program.get('Ext'), list):
                    self.__extProgram.append(program)
                elif tVar == RegisterEnum.folder_ext and isinstance(program.get('Folder_Ext'), list):
                    self.__folder_ext_Program.append(program)
                elif tVar == RegisterEnum.all:
                    self.__allProgram.append(program)

    def Start(self):
        print('Paratranz 项目助手',
              '1 - 从原始和汉化文件导出 ParaTranz 词条',
              '2 - 将 ParaTranz 词条写回汉化文件(localization)',
              '3 - 为 para_tranz_script.py 生成配置文件',
              '其它任意键 - 退出',
              sep='\n')
        userSelect = input('请输入您的选择：').strip()
        if userSelect == '1':
            for originalFile in self.__originalFilePaths:
                if self.__dealWithPath(originalFile) or self.__dealWithFolder(originalFile) or \
                        self.__dealWithExt(originalFile) or self.__dealWithFolderAndExt(originalFile) or \
                        self.__dealWithAll(originalFile):
                    continue
            self.__dealWithMission()
            print('翻译文件解析完毕。')
        elif userSelect == '2':
            for paratranzFile in self.__originalFilePaths:
                if not self.__changeExt(paratranzFile, 'json') in self.__paratranzOutputPaths:
                    continue
                if self.__dealWithPath(paratranzFile, True) or self.__dealWithFolder(paratranzFile, True) or \
                        self.__dealWithExt(paratranzFile, True) or self.__dealWithFolderAndExt(paratranzFile, True) or \
                        self.__dealWithAll(paratranzFile, True):
                    continue
            self.__dealWithMission(True)
            print('译文文件解析完毕。')
        elif userSelect == '3':
            from makeParaTranzConfig import preStartConfirm, makeConfigFile

            makeConfigFile(ORIGINAL_PATH, self.__originalFilePaths, **preStartConfirm())

    def __dealWithMission(self, funcID: bool = False):
        """战役系统处理器"""
        if isdir(sep.join([ORIGINAL_PATH, 'data', 'missions'])):
            for firstFolder in scandir(sep.join([ORIGINAL_PATH, 'data', 'missions'])):
                assert isinstance(firstFolder, DirEntry)
                if firstFolder.is_dir():
                    paratranzFileName = sep.join([PARA_TRANZ_PATH, 'data', 'missions', firstFolder.name + '.json'])
                    descriptorJSON = ''
                    missionTextTXT = ''
                    for secondFile in scandir(firstFolder.path):
                        assert isinstance(secondFile, DirEntry)
                        if secondFile.name == 'descriptor.json':
                            descriptorJSON = secondFile.path
                        elif secondFile.name == 'mission_text.txt':
                            missionTextTXT = secondFile.path
                    # 判断文件都存在
                    if len(descriptorJSON) * len(missionTextTXT) != 0:
                        if not funcID:
                            self.__makeDirs(paratranzFileName)
                            self.__executeFunc(self.__missionProgram.get('FromMission'), descriptorJSON, missionTextTXT,
                                               paratranzFileName)
                        else:
                            if isfile(paratranzFileName):
                                self.__executeFunc(self.__missionProgram.get('ToMission'), descriptorJSON,
                                                   missionTextTXT, paratranzFileName,
                                                   descriptorJSON.replace(ORIGINAL_PATH, TRANSLATION_PATH),
                                                   missionTextTXT.replace(ORIGINAL_PATH, TRANSLATION_PATH))

    def __dealWithPath(self, filePath: str, funcID: bool = False):
        # 路径处理器
        realFilePath = filePath.replace('/', sep)
        if not funcID:  # 翻译
            for program in self.__pathProgram:
                if filePath in program.get('Path'):
                    self.__makeDirs(PARA_TRANZ_PATH + realFilePath)
                    if self.__executeFunc(program.get('FromOriginal'), ORIGINAL_PATH + realFilePath,
                                          self.__changeExt(PARA_TRANZ_PATH + realFilePath, 'json')):
                        break  # 广播拦截
        else:  # 写回
            for program in self.__pathProgram:
                if filePath in program.get('Path'):
                    self.__makeDirs(TRANSLATION_PATH + realFilePath)
                    if self.__executeFunc(program.get('ToLocalization'), ORIGINAL_PATH + realFilePath,
                                          self.__changeExt(PARA_TRANZ_PATH + realFilePath, 'json'),
                                          TRANSLATION_PATH + realFilePath):
                        break  # 广播拦截

    def __dealWithFolder(self, filePath: str, funcID: bool = False):
        # 目录处理器
        realFilePath = filePath.replace('/', sep)
        folderPath = filePath.rpartition('/')[0]
        if not funcID:  # 翻译
            for program in self.__folderProgram:
                if folderPath in program.get('Folder') or f'{folderPath}/' in program.get('Folder'):
                    self.__makeDirs(PARA_TRANZ_PATH + realFilePath)
                    if self.__executeFunc(program.get('FromOriginal'), ORIGINAL_PATH + realFilePath,
                                          self.__changeExt(PARA_TRANZ_PATH + realFilePath, 'json')):
                        break  # 广播拦截
        else:  # 写回
            for program in self.__folderProgram:
                if folderPath in program.get('Folder') or f'{folderPath}/' in program.get('Folder'):
                    self.__makeDirs(TRANSLATION_PATH + realFilePath)
                    if self.__executeFunc(program.get('ToLocalization'), ORIGINAL_PATH + realFilePath,
                                          self.__changeExt(PARA_TRANZ_PATH + realFilePath, 'json'),
                                          TRANSLATION_PATH + realFilePath):
                        break  # 广播拦截

    def __dealWithExt(self, filePath: str, funcID: bool = False):
        # 扩展名处理器
        realFilePath = filePath.replace('/', sep)
        fileExt = filePath.rpartition('/')[2].rpartition('.')[2]
        if not funcID:  # 翻译
            for program in self.__extProgram:
                if fileExt.lower() in program.get('Ext'):
                    self.__makeDirs(PARA_TRANZ_PATH + realFilePath)
                    if self.__executeFunc(program.get('FromOriginal'), ORIGINAL_PATH + realFilePath,
                                          self.__changeExt(PARA_TRANZ_PATH + realFilePath, 'json')):
                        break  # 广播拦截
        else:  # 写回
            for program in self.__extProgram:
                if fileExt.lower() in program.get('Ext'):
                    self.__makeDirs(TRANSLATION_PATH + realFilePath)
                    if self.__executeFunc(program.get('ToLocalization'), ORIGINAL_PATH + realFilePath,
                                          self.__changeExt(PARA_TRANZ_PATH + realFilePath, 'json'),
                                          TRANSLATION_PATH + realFilePath):
                        break  # 广播拦截

    def __dealWithFolderAndExt(self, filePath: str, funcID: bool = False):
        # 目录 + 扩展名 联合处理器
        realFilePath = filePath.replace('/', sep)
        fileExt = filePath.rpartition('/')[2].rpartition('.')[2]
        folderPath = filePath.rpartition('/')[0] + '/'
        if not funcID:  # 翻译
            for program in self.__folder_ext_Program:
                for tFolderPath, tExt in program.get('Folder_Ext'):
                    if folderPath == tFolderPath and tExt.lower() == fileExt.lower():
                        self.__makeDirs(PARA_TRANZ_PATH + realFilePath)
                        self.__executeFunc(program.get('FromOriginal'), ORIGINAL_PATH + realFilePath,
                                           self.__changeExt(PARA_TRANZ_PATH + realFilePath, 'json'))
                        break
        else:  # 写回
            for program in self.__folder_ext_Program:
                for tFolderPath, tExt in program.get('Folder_Ext'):
                    if folderPath == tFolderPath and tExt.lower() == fileExt.lower():
                        self.__makeDirs(TRANSLATION_PATH + realFilePath)
                        self.__executeFunc(program.get('ToLocalization'), ORIGINAL_PATH + realFilePath,
                                           self.__changeExt(PARA_TRANZ_PATH + realFilePath, 'json'),
                                           TRANSLATION_PATH + realFilePath)
                        break

    def __dealWithAll(self, filePath: str, funcID: bool = False):
        # 默认处理器，一般用不到
        realFilePath = filePath.replace('/', sep)
        if not funcID:  # 翻译
            for program in self.__allProgram:
                self.__makeDirs(PARA_TRANZ_PATH + realFilePath)
                if self.__executeFunc(program.get('FromOriginal'), ORIGINAL_PATH + realFilePath,
                                      self.__changeExt(PARA_TRANZ_PATH + realFilePath, 'json')):
                    break  # 广播拦截
        else:  # 写回
            for program in self.__allProgram:
                self.__makeDirs(TRANSLATION_PATH + realFilePath)
                if self.__executeFunc(program.get('ToLocalization'), ORIGINAL_PATH + realFilePath,
                                      self.__changeExt(PARA_TRANZ_PATH + realFilePath, 'json'),
                                      TRANSLATION_PATH + realFilePath):
                    break  # 广播拦截

    def __executeFunc(self, funcName: str, *args):
        if hasattr(self, funcName):
            callback_func = getattr(self, funcName)
            if callable(callback_func):
                # try:
                return callback_func(*args)
            # except:
            #     return False

    @staticmethod
    def __changeExt(targetPath: str, targetExtName: str):
        fileExt = targetPath.rpartition(sep)[2].rpartition('.')[2]
        return targetPath[:-len(fileExt)] + targetExtName

    @staticmethod
    def __scanSpecialPath(toScanFolder: str) -> List[str]:
        scanResult: List[str] = []

        def ScanDir(dirPath: str):
            if isdir(dirPath):
                for fileUnit in scandir(dirPath):
                    if isinstance(fileUnit, DirEntry):
                        ScanDir(fileUnit.path)
            elif isfile(dirPath):
                scanResult.append(dirPath.replace(toScanFolder, '').replace(sep, '/'))

        ScanDir(toScanFolder)
        return scanResult

    @property
    def Config(self) -> List[dict]:
        return self.__config

    @staticmethod
    def __makeDirs(toMakeDIR: str):
        """预先建立目录结构"""
        from os import makedirs
        from os.path import isdir

        if not toMakeDIR.endswith(sep):
            toMakeDIR = toMakeDIR.rpartition(sep)[0] + sep
        if isdir(toMakeDIR):
            return
        makedirs(toMakeDIR)


class QuotedSpecialData(NamedTuple):
    """JSON中非标准字符串（两端不带双引号）的替换信息缓存数据。"""
    specialData: List[Tuple[str, str]]

    def endTask(self, endContent: str) -> str:
        """
        在所有翻译完全替换后，将之前 **预处理的非紧要文本** 代换回原有形式。

        :param endContent: 已处理好的，等待写回文件的翻译数据。
        :return: 已经过代换处理的文本。
        """
        for unit in self.specialData:
            endContent = endContent.replace(unit[0], unit[1], 1)
        return endContent


class ParatranzDataUnit:
    key: str  # 词条的唯一ID
    original: str  # 词条的原文（待翻译文本）
    translation: str  # 词条的翻译
    stage: int  # 词条当前的状态，默认是0，即待翻译
    context: str  # 词条的上下文，比如词条的应用场景

    def __init__(self, key: str, original: str, context: str = None, **kwargs):
        """
        描述一个Paratranz的词条属性数据。

        :param key: 词条在Paratranz上显示的“键值”。
        :param original: 词条的原文，待翻译文本。
        :param context: 词条的上下文数据。
        """
        self.key = key
        self.original = original
        self.translation = kwargs.get('translation', '')
        self.stage = kwargs.get('stage', 0)
        self.context = context

    def asDict(self):
        return dict(key=self.key, original=self.original, translation=self.translation, stage=self.stage,
                    context=self.context)

    @property
    def isTranslated(self):
        """该词条是否被标记为已翻译、已检查（一校）或已审核？"""
        return self.stage in (1, 3, 5)


class SubParatranz(ParatrazProject):

    def ImportOneConfig(self, **kwargs):
        if kwargs.get('Register') == RegisterEnum.mission:
            self.Config.append({'Register': RegisterEnum.mission, 'FromMission': kwargs.get('FromMission').__name__,
                                'ToMission': kwargs.get('ToMission').__name__})
        else:
            fromOriginal = kwargs.get('FromOriginal')
            toLocalization = kwargs.get('ToLocalization')
            if callable(fromOriginal):
                fromOriginal = fromOriginal.__name__
            if callable(toLocalization):
                toLocalization = toLocalization.__name__
            # if 'Register' not in kwargs or kwargs.get('Register') not in RegisterEnum:
            #     return False
            if (kwargs.get('Register') == RegisterEnum.path and not isinstance(kwargs.get('Path'), list)) or \
                    (kwargs.get('Register') == RegisterEnum.folder and not isinstance(kwargs.get('Folder'), list)) or \
                    (kwargs.get('Register') == RegisterEnum.ext and not isinstance(kwargs.get('Ext'), list)) or \
                    (kwargs.get('Register') == RegisterEnum.folder_ext and not isinstance(kwargs.get('Folder_Ext'),
                                                                                          list)):
                return False
            if not (isinstance(fromOriginal, str) and isinstance(toLocalization, str)):
                return False
            if not (callable(getattr(self, fromOriginal)) and callable(getattr(self, toLocalization))):
                return False
            # 开始动真格的
            thisConfig = {'Register': kwargs.get('Register'), 'FromOriginal': fromOriginal,
                          'ToLocalization': toLocalization}
            if kwargs.get('Register') == RegisterEnum.path:
                thisConfig['Path'] = kwargs.get('Path')
            elif kwargs.get('Register') == RegisterEnum.folder:
                thisConfig['Folder'] = kwargs.get('Folder')
            elif kwargs.get('Register') == RegisterEnum.ext:
                thisConfig['Ext'] = kwargs.get('Ext')
            elif kwargs.get('Register') == RegisterEnum.folder_ext:
                thisConfig['Folder_Ext'] = kwargs.get('Folder_Ext')
            self.Config.append(thisConfig)

    def ImportConfig(self):
        # 原版 - 战役外置文件的统一处理模块
        self.ImportOneConfig(Register=RegisterEnum.mission, FromMission=self.inMissions, ToMission=self.outMissions)
        # 原版 - 代码中的字符串外置文件
        self.ImportOneConfig(Register=RegisterEnum.path, Path=['/data/strings/strings.json'],
                             FromOriginal=self.inStringsJSON, ToLocalization=self.outStringsJSON)
        # 原版 - 势力相关配置文件
        self.ImportOneConfig(Register=RegisterEnum.folder_ext, Folder_Ext=[('/data/world/factions/', 'faction')],
                             FromOriginal=self.inFactions, ToLocalization=self.outFactions)
        # 原版 - 出现在S/L页面和主界面的游戏提示
        self.ImportOneConfig(Register=RegisterEnum.path, Path=['/data/strings/tips.json'],
                             FromOriginal=self.inTips, ToLocalization=self.outTips)
        # 战斗骚话mod - 相关战斗对话内容
        self.ImportOneConfig(Register=RegisterEnum.folder_ext,
                             Folder_Ext=[('/data/config/chatter/characters/', 'json')],
                             FromOriginal=self.inChatter, ToLocalization=self.outChatter)
        # 势力争霸mod - 玩家可选的自定义开局
        self.ImportOneConfig(Register=RegisterEnum.path, Path=['/data/config/exerelin/customStarts.json'],
                             FromOriginal=self.inCustomStart, ToLocalization=self.outCustomStart)
        # 原版 - 默认阶层（Rank）相关配置
        self.ImportOneConfig(Register=RegisterEnum.path, Path=['/data/world/factions/default_ranks.json'],
                             FromOriginal=self.inDefaultRanks, ToLocalization=self.outDefaultRanks)
        # MagicLib mod - 高价值赏金（HVB）的相关内容
        self.ImportOneConfig(Register=RegisterEnum.path, Path=['/data/config/modFiles/magicBounty_data.json'],
                             FromOriginal=self.inMagicBountyData, ToLocalization=self.outMagicBountyData)
        # LunaLib mod - 一些用于在游戏中动态调整mod的数值的mod的相关配置
        self.ImportOneConfig(Register=RegisterEnum.path, Path=['/data/config/LunaSettings.csv'],
                             FromOriginal=self.inLunaSettings, ToLocalization=self.outLunaSettings)
        # 势力争霸mod - 势力建立同盟时的名称相关配置
        self.ImportOneConfig(Register=RegisterEnum.path, Path=['/data/config/exerelin/allianceNames.json'],
                             FromOriginal=self.inAllianceNames, ToLocalization=self.outAllianceNames)
        # 势力争霸mod - 势力间进行外交的相关配置（但主要是处理事件名称和描述）
        self.ImportOneConfig(Register=RegisterEnum.path, Path=['/data/config/exerelin/diplomacyConfig.json'],
                             FromOriginal=self.inDiplomacyConfig, ToLocalization=self.outDiplomacyConfig)
        # 势力争霸mod - 一个势力在势力争霸环境下所使用的舰队名称和其他特殊信息
        self.ImportOneConfig(Register=RegisterEnum.folder_ext,
                             Folder_Ext=[('/data/config/exerelinFactionConfig/', 'json')],
                             FromOriginal=self.inExerelinFactionConfig, ToLocalization=self.outExerelinFactionConfig)
        # 星舰传奇mod - 目前只处理一个显示
        self.ImportOneConfig(Register=RegisterEnum.path,
                             Path=['/data/config/starship_legends/factionConfigurations.json'],
                             FromOriginal=self.inFactionConfigurations, ToLocalization=self.outFactionConfigurations)
        # 原版 - 联络人的相关分类属性
        self.ImportOneConfig(Register=RegisterEnum.path, Path=['/data/config/contact_tag_data.json'],
                             FromOriginal=self.inContactTagData, ToLocalization=self.outContactTagData)
        # 原版 - 舰船具体配置文件（231229：经向猫猫询问得知，该部分无需翻译）
        # self.ImportOneConfig(Register=folder_ext, Folder_Ext=[('/data/hulls/', 'ship')],
        #                      FromOriginal=self.inShipFile, ToLocalization=self.outShipFile)
        # 原版 - 舰船涂装配置
        self.ImportOneConfig(Register=RegisterEnum.folder_ext, Folder_Ext=[('/data/hulls/skins/', 'skin')],
                             FromOriginal=self.inHullSkinFile, ToLocalization=self.outHullSkinFile)
        # 工业革命mod - 宠物死因列表
        self.ImportOneConfig(Register=RegisterEnum.path,
                             Path=['/data/strings/hamster_death_causes.csv', '/data/strings/combat_death_causes.csv'],
                             FromOriginal=self.inDeathCauses, ToLocalization=self.outDeathCauses)
        # 原版 - 自定义天体
        self.ImportOneConfig(Register=RegisterEnum.path, Path=['/data/config/custom_entities.json'],
                             FromOriginal=self.inCustomEntity, ToLocalization=self.outCustomEntity)
        # 原版 - Mod简介
        self.ImportOneConfig(Register=RegisterEnum.path, Path=['/mod_info.json'],
                             FromOriginal=self.inModInfo, ToLocalization=self.outModInfo)
        # 原版 - 行星类型（planets.json）的数据
        self.ImportOneConfig(Register=RegisterEnum.path, Path=['/data/config/planets.json'],
                             FromOriginal=self.inPlanets, ToLocalization=self.outPlanets)
        # 原版 - 局部战斗中的可占领战术点（比如通讯中继站/传感干扰器）数据
        self.ImportOneConfig(Register=RegisterEnum.path, Path=['/data/config/battle_objectives.json'],
                             FromOriginal=self.inBattleObjectives, ToLocalization=self.outBattleObjectives)
        # 原版 - settings.json中的数据
        self.ImportOneConfig(Register=RegisterEnum.path, Path=['/data/config/settings.json'],
                             FromOriginal=self.inSettings, ToLocalization=self.outSettings)

    # data/missions/*
    def inMissions(self, *args):
        result = []
        with open(args[0], encoding='UTF-8') as tFile:
            tContent: dict = json5.loads(self.__filterJSON5(tFile.read()))
            for unit in ('title', 'difficulty'):
                if unit in tContent:
                    result.append(self.__buildDict('mission#' + unit, tContent[unit]))
        with open(args[1], encoding='UTF-8') as tFile:
            result.append(self.__buildDict('mission#text', tFile.read()))
        self.__writeParatranzJSON(result, args[2])

    def outMissions(self, *args):
        with open(args[0], encoding='UTF-8') as tFile:
            tContent: dict = json5.loads(self.__filterJSON5(tFile.read()))
        for unit in self.__readParatranzJSON(args[2]):
            if unit.isTranslated:
                if unit.key == 'mission#text':
                    with open(args[4], 'w', encoding='UTF-8') as tFile:
                        tFile.write(self.__getTranslation(unit))
                else:
                    realID = unit.key.split('#')[1]
                    if realID in tContent:
                        tContent[realID] = self.__getTranslation(unit)
        with open(args[3], 'w', encoding='UTF-8') as tFile:
            json5.dump(tContent, tFile, ensure_ascii=False, indent=4, quote_keys=True)

    # data/strings/strings.json
    def inStringsJSON(self, *args):
        with open(args[0], encoding='UTF-8') as tFile:
            tFileContent = self.__filterJSON5(tFile.read())
        # 读取JSON
        commentCode = {}
        searchHint = re.compile('[^\\\\]",?[ \t]*//')
        for line in tFileContent.splitlines():
            if '\"' in line and searchHint.search(line) is not None:
                commentCode[line.split('\"')[1]] = line[searchHint.search(line).end():].strip()
        # 解析注释完成
        originalJSON5: Dict[str, Dict[str, str]] = json5.loads(tFileContent)
        result = []
        for firstKey in originalJSON5.keys():
            for secondKey in originalJSON5.get(firstKey).keys():
                lineConfig = self.__buildDict(f'{firstKey}#{secondKey}', originalJSON5[firstKey][secondKey])
                if secondKey in commentCode:
                    lineConfig.context = commentCode.pop(secondKey).strip()
                result.append(lineConfig)
        # 写入文件
        self.__writeParatranzJSON(result, args[1])

    def outStringsJSON(self, *args):
        tTranslation = self.__readParatranzJSON(args[1])
        # 读取内容
        result = {}
        for unit in tTranslation:
            keyID = unit.key.split('#')
            if keyID[0] not in result:
                result[keyID[0]] = {}
            if unit.isTranslated and len(self.__getTranslation(unit)) > 0:
                result.get(keyID[0])[keyID[1]] = self.__getTranslation(unit)
            else:
                result.get(keyID[0])[keyID[1]] = unit.original  # 不至于出现什么missing_string
        # 处理完成
        with open(args[2], 'w', encoding='UTF-8') as tFile:
            json5.dump(result, tFile, ensure_ascii=False, indent=4, quote_keys=True)

    # data/world/factions/*.faction
    def inFactions(self, *args):
        with open(args[0], encoding='UTF-8') as tFile:
            tFileContent: dict = json5.loads(
                self.__quoteSpecialDataForIn(re.compile('^"?tags"?: *\\['), self.__filterJSON5(tFile.read())))
        # 预定义关键字解析
        result = []
        # 240819：增补了对势力文件中部分势力名称Key的注解
        hintDict = {'displayName': '势力短名称', 'displayNameWithArticle': '带冠词的势力短名称',
                    'displayNameLong': '势力的书面正式名称', 'displayNameLongWithArticle': '带冠词的势力的书面正式名称'}
        for strKey in ('displayName', 'displayNameWithArticle', 'displayNameLong', 'displayNameLongWithArticle',
                       'displayNameIsOrAre'):
            if strKey in tFileContent:
                result.append(self.__buildDict(f'root#{strKey}', tFileContent.get(strKey), hintDict.get(strKey)))
                if strKey == 'displayNameIsOrAre':  # 240729：往刚刚增加的翻译文本里覆写默认数据
                    result[-1].translation = '是'
                    result[-1].stage = 1
        # 名字好了
        if 'ranks' in tFileContent:
            ranksDict: Dict[str, Dict[str, Dict[str, str]]] = tFileContent.get('ranks')
            for firstKey in ranksDict.keys():
                for secondKey in ranksDict.get(firstKey).keys():
                    if 'name' in ranksDict.get(firstKey).get(secondKey):
                        result.append(self.__buildDict(f"ranks#{firstKey}#{secondKey}#name",
                                                       ranksDict.get(firstKey).get(secondKey).get('name'),
                                                       '通讯目录/舰船对话中的人显示的阶级（Rank）名称'))
        # 阶级？
        if 'fleetTypeNames' in tFileContent:
            fleetNames: Dict[str, str] = tFileContent.get('fleetTypeNames')
            # 240819：增补了对势力文件中舰队名称部分Key的注解
            hintDict = {'trade': '势力派出的大型贸易舰队的名称', 'tradeLiner': '势力派出的前往Galatia学院的航班的名称',
                        'tradeSmuggler': '由该势力派出的，在势力之间走私商品的走私舰队名称',
                        'smallTrader': '势力派出的小型贸易舰队的名称', 'patrolSmall': '势力派出的小型巡逻队的名称',
                        'patrolMedium': '势力派出的中型巡逻队的名称', 'patrolLarge': '势力派出的大型巡逻队的名称'}
            for firstKey in fleetNames.keys():
                result.append(self.__buildDict(f'fleetTypeNames#{firstKey}', fleetNames.get(firstKey),
                                               hintDict.get(firstKey)))
        self.__writeParatranzJSON(result, args[1])

    def outFactions(self, *args):
        with open(args[0], encoding='UTF-8') as tFile:
            preContent, toReplaceData = self.__quoteSpecialDataForOut(re.compile('^"?tags"?: *\\['),
                                                                      self.__filterJSON5(tFile.read()))
            tOriginal: dict = json5.loads(preContent)
        # 读取原文文件内容
        tTranslation = self.__readParatranzJSON(args[1])
        # 读取译文文件内容
        for unit in tTranslation:
            if not unit.isTranslated:
                continue
            keyID: str = unit.key
            translation: str = self.__getTranslation(unit)
            if len(translation) == 0:
                translation = unit.original  # 确保始终有数据，不至于直接游戏中报错
            if keyID.startswith('root#'):
                realKey = keyID.split('root#')[1]
                if realKey in tOriginal:
                    tOriginal[realKey] = translation
            elif keyID.startswith('fleetTypeNames#') and 'fleetTypeNames' in tOriginal:
                realKey = keyID.split('fleetTypeNames#')[1]
                if realKey in tOriginal.get('fleetTypeNames'):
                    tOriginal.get('fleetTypeNames')[realKey] = translation
            elif keyID.startswith('ranks#'):
                realKey = keyID[6:].split('#')
                countID = 0
                a_dict = tOriginal.get('ranks')
                while True:
                    if countID == len(realKey) - 1:
                        a_dict[realKey[countID]] = translation
                        break
                    elif realKey[countID] in a_dict:
                        a_dict = a_dict.get(realKey[countID])
                    else:
                        break
                    countID += 1
        with open(args[2], 'w', encoding='UTF-8') as tFile:
            tFile.write(toReplaceData.endTask(json.dumps(tOriginal, ensure_ascii=False, indent=4)))

    # data/strings/tips.json
    def inTips(self, *args):
        tFile = open(args[0], encoding='UTF-8')
        tOriginal: dict = json5.loads(self.__filterJSON5(tFile.read()))
        tFile.close()
        # 读取原文文件内容
        result = []
        for strUnit in tOriginal.get('tips'):  # 以原文MD5作为唯一key，从而规避掉顺序改变引起的Paratranz重复劳动
            if isinstance(strUnit, str):
                result.append(self.__buildDict(f'tips#{self.__simpleMD5(strUnit)}', strUnit))
            elif isinstance(strUnit, dict):
                result.append(
                    self.__buildDict(f'tips#{self.__simpleMD5(strUnit.get("tip"))}${strUnit.get("freq")}', strUnit.get('tip')))
        self.__writeParatranzJSON(result, args[1])

    def outTips(self, *args):
        tTranslation = self.__readParatranzJSON(args[1])
        result = {'tips': []}
        for unit in tTranslation:
            if unit.isTranslated:
                if '$' not in unit.key:
                    result['tips'].append(self.__getTranslation(unit))
                else:
                    result['tips'].append(
                        {'freq': float(unit.key.split('$')[1]), 'tip': self.__getTranslation(unit)})
        tFile = open(args[2], 'w', encoding='UTF-8')
        json5.dump(result, tFile, ensure_ascii=False, indent=4, quote_keys=True)
        tFile.close()

    # data/config/chatter/characters/*.json
    def inChatter(self, *args):
        with open(args[0], encoding='UTF-8') as tFile:
            tContent: dict = json5.loads(self.__filterJSON5(tFile.read()))
        tVar: Dict[str, List[Dict[str, str]]] = tContent.pop('lines')
        result = []
        personName = tContent.get('name')
        for firstKey in tVar.keys():
            count = 1
            for lineText in tVar.get(firstKey):
                result.append(self.__buildDict(f'chatter#{personName}${firstKey}@{count}', lineText['text'],
                                               f'当 {personName} 出现了 {firstKey} 的情况时'))
                count += 1
        self.__writeParatranzJSON(result, args[1])

    def outChatter(self, *args):
        with open(args[0], encoding='UTF-8') as tFile:
            tOriginal: dict = json5.loads(self.__filterJSON5(tFile.read()))
        tTranslation = self.__readParatranzJSON(args[1])
        result = {}
        for unit in tTranslation:
            if unit.isTranslated:
                firstKey = unit.key.split('$')[1].rpartition('@')[0]
                if firstKey not in result:
                    result[firstKey] = [{'text': self.__getTranslation(unit)}]
                else:
                    result[firstKey].append({'text': self.__getTranslation(unit)})
        tOriginal.update({'lines': result})
        with open(args[2], 'w', encoding='UTF-8') as tFile:
            json5.dump(tOriginal, tFile, ensure_ascii=False, indent=4, quote_keys=True)

    # data/config/exerelin/customStarts.json
    def inCustomStart(self, *args):
        with open(args[0], encoding='UTF-8') as tFile:
            tContent: List[dict] = json5.loads(self.__filterJSON5(tFile.read()))['starts']
        result = []
        for unit in tContent:
            unitID = unit.get('id')
            result.append(self.__buildDict(f'{unitID}#name', unit.get('name')))
            result.append(self.__buildDict(f'{unitID}#difficulty', unit.get('difficulty')))
            result.append(self.__buildDict(f'{unitID}#desc', unit.get('desc')))
        self.__writeParatranzJSON(result, args[1])

    def outCustomStart(self, *args):
        tOriginal = {}
        with open(args[0], encoding='UTF-8') as tFile:
            tContent: List[dict] = json5.loads(self.__filterJSON5(tFile.read()))['starts']
            for unit in tContent:
                tOriginal[unit.get('id')] = unit
        for unit in self.__readParatranzJSON(args[1]):
            if unit.isTranslated:
                unitID, unitKey = unit.key.split('#')
                if unitID in tOriginal:
                    tOriginal[unitID][unitKey] = self.__getTranslation(unit)
        with open(args[2], 'w', encoding='UTF-8') as tFile:
            json5.dump({'starts': list(tOriginal.values())}, tFile, ensure_ascii=False, indent=4, quote_keys=True)

    # data/config/exerelin/allianceNames.json
    def inAllianceNames(self, *args):
        with open(args[0], encoding='UTF-8') as tFile:
            tOriginal: Dict[str, Dict[str, Dict[str, List[str]]]] = json5.loads(self.__filterJSON5(tFile.read()))
        result = []
        for firstKey in tOriginal.keys():
            for secondKey in tOriginal[firstKey].keys():
                for thirdKey in tOriginal[firstKey][secondKey].keys():
                    t1 = tOriginal[firstKey][secondKey][thirdKey]
                    if isinstance(t1, list):
                        for i in range(len(t1)):
                            result.append(self.__buildDict(f"{firstKey}#{secondKey}${thirdKey}%{i + 1}", t1[i],
                                                           f"当势力 {secondKey}与{thirdKey} 结盟时，可选的默认名字之一"))
        self.__writeParatranzJSON(result, args[1])

    def outAllianceNames(self, *args):
        tResult = {}
        for unit in self.__readParatranzJSON(args[1]):
            if unit.isTranslated:
                firstKey, t1 = unit.key.split('#')
                secondKey, thirdKey = t1.split('$')
                if '%' in thirdKey:
                    thirdKey = thirdKey.split('%')[0]
                if firstKey not in tResult:
                    tResult[firstKey] = {}
                if secondKey not in tResult[firstKey]:
                    tResult[firstKey][secondKey] = {}
                if thirdKey not in tResult[firstKey][secondKey]:
                    tResult[firstKey][secondKey][thirdKey] = [self.__getTranslation(unit)]
                else:
                    tResult[firstKey][secondKey][thirdKey].append(self.__getTranslation(unit))
        with open(args[2], 'w', encoding='UTF-8') as tFile:
            json5.dump(tResult, tFile, ensure_ascii=False, indent=4, quote_keys=True)

    # data/config/exerelin/diplomacyConfig.json
    def inDiplomacyConfig(self, *args):
        # 只处理event区块
        with open(args[0], encoding="UTF-8") as tFile:
            tOriginal: List[dict] = json5.loads(self.__filterJSON5(tFile.read()))['events']
        result = []
        for eventUnit in tOriginal:
            stageID = eventUnit.get('stage')
            result.append(
                self.__buildDict(f'event#{stageID}$name', eventUnit.get('name'),
                                 "外交事件：\n" + pprint.pformat(eventUnit, sort_dicts=False)))
            result.append(
                self.__buildDict(f'event#{stageID}$desc', eventUnit.get('desc'),
                                 "外交事件：\n" + pprint.pformat(eventUnit, sort_dicts=False)))
        self.__writeParatranzJSON(result, args[1])

    def outDiplomacyConfig(self, *args):
        with open(args[0], encoding='UTF-8') as tFile:
            tOriginal: dict = json5.loads(self.__filterJSON5(tFile.read()))
        tEvent: List[dict] = tOriginal['events']
        for unit in self.__readParatranzJSON(args[1]):
            if unit.isTranslated:
                stageID, unitKey = unit.key.split('#')[1].split('$')
                for stageUnit in tEvent:
                    if stageUnit.get('stage') == stageID:
                        stageUnit[unitKey] = self.__getTranslation(unit)
                        break
        with open(args[2], 'w', encoding='UTF-8') as tFile:
            json5.dump(tOriginal, tFile, ensure_ascii=False, indent=4, quote_keys=True)

    # data/world/factions/default_ranks.json
    def inDefaultRanks(self, *args):
        with open(args[0], encoding='UTF-8') as tFile:
            tOriginal: Dict[str, Dict[str, Dict[str, str]]] = json5.loads(self.__filterJSON5(tFile.read()))
        result = []
        for firstKey in tOriginal.keys():
            for secondKey in tOriginal[firstKey].keys():
                for thirdKey in tOriginal[firstKey][secondKey].keys():
                    if isinstance(tOriginal[firstKey][secondKey][thirdKey], str):
                        result.append(self.__buildDict(f'{firstKey}#{secondKey}${thirdKey}',
                                                       tOriginal[firstKey][secondKey][thirdKey]))
        self.__writeParatranzJSON(result, args[1])

    def outDefaultRanks(self, *args):
        with open(args[0], encoding='UTF-8') as tFile:
            tOriginal: Dict[str, Dict[str, Dict[str, str]]] = json5.loads(self.__filterJSON5(tFile.read()))
        for unit in self.__readParatranzJSON(args[1]):
            if unit.isTranslated:
                firstKey, tVar = unit.key.split('#')
                secondKey, thirdKey = tVar.split('$')
                if firstKey in tOriginal.keys() and secondKey in tOriginal[firstKey].keys() and thirdKey in \
                        tOriginal[firstKey][secondKey]:
                    tOriginal[firstKey][secondKey][thirdKey] = self.__getTranslation(unit)
        with open(args[2], 'w', encoding='UTF-8') as tFile:
            json5.dump(tOriginal, tFile, ensure_ascii=False, indent=4, quote_keys=True)

    # data/config/modFiles/magicBounty_data.json
    def inMagicBountyData(self, *args):
        """这部分处理的是MagicLib的自带HVB部分。"""
        with open(args[0], encoding='UTF-8') as tFile:
            tOriginal: Dict[str, dict] = json5.loads(self.__filterJSON5(tFile.read()))
        result = []
        # 240819：增补了对高价值赏金（HVB）中部分Key的注解
        hintDict = {'job_name': '赏金名称', 'job_description': '赏金的说明文本', 'job_comm_reply': '玩家与赏金目标进行交互时，对面给的回复', 'job_intel_success': '赏金完成后，玩家在网络信息面板上看到的消息文本。', 'job_intel_failure': '赏金舰队被非玩家摧毁后，玩家在网络信息面板上看到的消息文本。', 'fleet_name': '赏金目标的舰队名称', 'fleet_flagship_name': '赏金目标的座舰的名称', 'job_intel_expired': '赏金超期而未被完成，玩家在网络信息面板上看到的消息文本。', 'job_difficultyDescription': '赏金的难度描述文本（推测）。'}
        for bountyID in tOriginal:
            for paraName in hintDict.keys():
                if paraName in tOriginal[bountyID]:
                    result.append(self.__buildDict(f'{bountyID}#{paraName}', tOriginal[bountyID].get(paraName),
                                                   f'{hintDict.get(paraName)}\n\n[本行原始数据]\n{pprint.pformat(tOriginal[bountyID], sort_dicts=False)}'))
        self.__writeParatranzJSON(result, args[1])

    def outMagicBountyData(self, *args):
        self.__commonTranslateFunc_v2(*args)

    # data/config/exerelinFactionConfig/*.json
    def inExerelinFactionConfig(self, *args):
        toTranslateKeys = ('ngcTooltip', 'rebelFleetSuffix', 'asteroidMiningFleetName', 'gasMiningFleetName',
                           'invasionFleetName', 'responseFleetName', 'invasionSupportFleetName', 'defenceFleetName',
                           'suppressionFleetName', 'vengeanceLevelNames', 'vengeanceFleetNames',
                           'vengeanceFleetNamesSingle')
        # 240819：增补了对势力争霸mod中部分舰队名称Key的注解
        hintDict = {'rebelFleetSuffix': '势力争霸mod中的重生舰队名称后缀',
                    'asteroidMiningFleetName': '势力争霸mod中从殖民地派出的小行星采矿舰队名称',
                    'gasMiningFleetName': '势力争霸mod中从殖民地派出的挥发物开采舰队的名称',
                    'invasionFleetName': '势力争霸mod中的入侵舰队名称',
                    'invasionSupportFleetName': '势力争霸mod中的入侵辅助舰队名称',
                    'defenceFleetName': '势力争霸mod中势力派出的防御舰队的名称',
                    'suppressionFleetName': '势力争霸mod中势力派出用于镇压殖民地叛乱的支援舰队的名称',
                    'vengeanceLevelNames': '势力争霸mod中派出的复仇舰队名称',
                    'vengeanceFleetNames': '势力争霸mod中派出的复仇舰队名称',
                    'vengeanceFleetNamesSingle': '势力争霸mod中派出的复仇舰队名称'}
        with open(args[0], encoding='UTF-8') as tFile:
            tOriginal: dict = json5.loads(self.__filterJSON5(tFile.read()))
        result = []
        for translateKey in toTranslateKeys:
            if translateKey in tOriginal:
                if isinstance(tOriginal.get(translateKey), str):
                    result.append(self.__buildDict(translateKey, tOriginal.get(translateKey), hintDict.get(translateKey)))
                elif isinstance(tOriginal.get(translateKey), list):
                    for unitID in range(len(tOriginal.get(translateKey))):
                        if isinstance(tOriginal.get(translateKey)[unitID], str):
                            result.append(
                                self.__buildDict(f'{translateKey}${unitID}', tOriginal.get(translateKey)[unitID],
                                                 hintDict.get(translateKey)))
        self.__writeParatranzJSON(result, args[1])

    def outExerelinFactionConfig(self, *args):
        with open(args[0], encoding='UTF-8') as tFile:
            tOriginal: dict = json5.loads(self.__filterJSON5(tFile.read()))
        for unit in self.__readParatranzJSON(args[1]):
            if unit.isTranslated:
                if unit.key in tOriginal:
                    tOriginal[unit.key] = self.__getTranslation(unit)
                elif '$' in unit.key:  # 单层数组替换操作
                    first, second = unit.key.split('$')
                    if first in tOriginal:
                        tOriginal[first][int(second)] = self.__getTranslation(unit)
        with open(args[2], 'w', encoding='UTF-8') as tFile:
            json5.dump(tOriginal, tFile, ensure_ascii=False, indent=4, quote_keys=True)

    # data/config/starship_legends/factionConfigurations.json
    def inFactionConfigurations(self, *args):
        # 一看就是星舰传奇的玩意
        with open(args[0], encoding='UTF-8') as tFile:
            tOriginal: Dict[str, dict] = json5.loads(self.__filterJSON5(tFile.read()))
        result = []
        for firstKey in tOriginal:
            if 'descriptionOverride' in tOriginal[firstKey].keys():
                result.append(
                    self.__buildDict(f'{firstKey}#descriptionOverride', tOriginal[firstKey]['descriptionOverride']))
        self.__writeParatranzJSON(result, args[1])

    def outFactionConfigurations(self, *args):
        self.__commonTranslateFunc_v2(*args)

    # data/config/contact_tag_data.json
    def inContactTagData(self, *args):
        with open(args[0], encoding='UTF-8') as tFile:
            tOriginal: Dict[str, dict] = json5.loads(self.__filterJSON5(tFile.read()))
        result = []
        for firstKey in tOriginal:
            if 'name' in tOriginal[firstKey]:
                result.append(self.__buildDict(f'{firstKey}#name', tOriginal[firstKey]['name']))
        self.__writeParatranzJSON(result, args[1])

    def outContactTagData(self, *args):
        self.__commonTranslateFunc_v2(*args)

    # data/hulls/*.ship
    def inShipFile(self, *args):
        with open(args[0], encoding='UTF-8') as tFile:
            tOriginal: dict = json5.loads(self.__filterJSON5(tFile.read()))
        result = []
        if 'hullName' in tOriginal:
            result.append(self.__buildDict(f'root#hullName', tOriginal['hullName'],
                                           f'[本行原始数据]\n{pprint.pformat(tOriginal, sort_dicts=False)}'))
        self.__writeParatranzJSON(result, args[1])

    def outShipFile(self, *args):
        self.__commonTranslateFunc_v1(*args)

    # data/hulls/skins/*.skin
    def inHullSkinFile(self, *args):
        with open(args[0], encoding='UTF-8') as tFile:
            tOriginal: dict = json5.loads(self.__quoteSpecialDataForIn(re.compile('^"?(hints|removeHints|addHints)"?:'),
                                                                       self.__filterJSON5(tFile.read())))
        result = []
        for keyStr in ('hullName', 'descriptionPrefix', 'tech'):
            if keyStr in tOriginal:
                result.append(self.__buildDict(f'root#{keyStr}', tOriginal[keyStr],
                                               f'[本行原始数据]\n{pprint.pformat(tOriginal, sort_dicts=False)}'))
        self.__writeParatranzJSON(result, args[1])

    def outHullSkinFile(self, *args):
        with open(args[0], encoding='UTF-8') as tFile:
            preContent, toReplaceData = self.__quoteSpecialDataForOut(re.compile('^"?(hints|removeHints|addHints)"?:'),
                                                                      self.__filterJSON5(tFile.read()))
            tOriginal = json5.loads(preContent)
        for unit in self.__readParatranzJSON(args[1]):
            if unit.isTranslated:
                keyStr = unit.key.split('#')[1]
                if keyStr in tOriginal:
                    tOriginal[keyStr] = self.__getTranslation(unit)
        with open(args[2], 'w', encoding='UTF-8') as tFile:
            tFile.write(toReplaceData.endTask(json.dumps(tOriginal, ensure_ascii=False, indent=4)))

    # data/strings/combat_death_causes.csv 和 data/strings/hamster_death_causes.csv
    # 处理宠物系统的死因描述
    def inDeathCauses(self, *args):
        result = []
        with open(args[0], encoding='UTF-8') as tFile:
            for line in list(csv.DictReader(tFile)):
                contextText = None
                if 'combat' in args[0]:
                    contextText = '该宠物在战斗中与被毁舰船一起共存亡了'
                elif 'hamster' in args[0]:
                    contextText = '这是一只hamster（仓鼠），自然死亡时的死因描述'
                result.append(self.__buildDict(f'id#{self.__simpleMD5(line["id"])}', line['id'], contextText))
        self.__writeParatranzJSON(result, args[1])

    def outDeathCauses(self, *args):
        result = []
        for unit in self.__readParatranzJSON(args[1]):
            if unit.isTranslated:
                result.append({'id': self.__getTranslation(unit)})
        with open(args[2], 'w', newline='', encoding='UTF-8') as tFile:
            tVar = csv.DictWriter(tFile, ['id'])
            tVar.writeheader()
            tVar.writerows(result)

    # data/config/custom_entities.json
    def inCustomEntity(self, *args):
        with open(args[0], encoding='UTF-8') as tFile:
            tOriginal: dict = json5.loads(
                self.__quoteSpecialDataForIn(re.compile('^"layers":'), self.__filterJSON5(tFile.read())))
        result = []
        for firstKey in tOriginal:
            secondDict: dict = tOriginal[firstKey]
            for unit in ('defaultName', 'nameInText', 'shortName', 'aOrAn', 'isOrAre'):
                if unit in secondDict and len(secondDict[unit]) > 0:
                    result.append(self.__buildDict(f'{firstKey}#{unit}', secondDict[unit],
                                                   f'[本行原始数据]\n{pprint.pformat(secondDict, sort_dicts=False)}'))
                    if unit == 'aOrAn':
                        result[-1].stage = 1
                        result[-1].translation = '一个'
                    elif unit == 'isOrAre':
                        result[-1].stage = 1
                        result[-1].translation = '是'
        self.__writeParatranzJSON(result, args[1])

    def outCustomEntity(self, *args):
        with open(args[0], encoding='UTF-8') as tFile:
            preContent, toReplaceData = self.__quoteSpecialDataForOut(re.compile('^"layers"'),
                                                                      self.__filterJSON5(tFile.read()))
            tOriginal: dict = json5.loads(preContent)
        for unit in self.__readParatranzJSON(args[1]):
            if unit.isTranslated:
                firstKey, secondKey = unit.key.split('#')
                if firstKey in tOriginal:
                    tOriginal[firstKey][secondKey] = self.__getTranslation(unit)
        preResult = toReplaceData.endTask(json5.dumps(tOriginal, ensure_ascii=False, indent=4, quote_keys=True))
        with open(args[2], 'w', encoding='UTF-8') as tFile:
            tFile.write(preResult)

    # data/config/LunaSettings.csv
    # 本来这个文件应该交给汉化组写的脚本处理，但是由于某些原因……
    def inLunaSettings(self, *args):
        result = []
        with open(args[0], encoding='UTF-8') as tFile:
            tVar = list(csv.DictReader(tFile))
            tVar1 = self.__extractDuplicateKeyText(tVar, 'fieldID')  # 预提取重复的ID信息数据
            for tabUnit in self.__extractDuplicateKeyText(tVar, 'tab').keys():
                if tabUnit != '':
                    result.append(self.__buildDict(f'tabValue${len(result) + 1}', tabUnit, '这个是Tab页的标签头'))
            for lineDict in tVar:
                line_FieldID: str = lineDict['fieldID']
                if line_FieldID.strip().startswith('#'):
                    continue
                extraNumber = ''
                if line_FieldID == '':
                    continue
                if line_FieldID in tVar1:  # 需要特别关照的重复键值将打上不同的ID，以便paratranz能认出来
                    extraNumber = f'${tVar1[line_FieldID]}'
                    tVar1[line_FieldID] += 1
                if lineDict['fieldType'] in ('Header', 'Text'):  # 检测到特殊头部信息
                    result.append(
                        self.__buildDict(f'{line_FieldID}#defaultValue{extraNumber}', lineDict['defaultValue'],
                                         f'[本行原始数据]\n{pprint.pformat(lineDict, sort_dicts=False)}'))
                elif lineDict['fieldType'] == 'Radio':  # 字符串单选数据特别处理
                    for keyStr in ('fieldName', 'fieldDescription', 'defaultValue'):
                        if keyStr in lineDict and lineDict[keyStr].strip() != '':
                            result.append(self.__buildDict('{0}#{1}{2}'.format(line_FieldID, keyStr, extraNumber),
                                                           lineDict[keyStr],
                                                           f'[本行原始数据]\n{pprint.pformat(lineDict, sort_dicts=False)}'))
                    result.append(self.__buildDict('{0}#{1}{2}'.format(line_FieldID, 'secondaryValue', extraNumber),
                                                   lineDict['secondaryValue'],
                                                   f'注意：请在翻译时保留英文逗号，它是数据之间的分割线！如果一定要使用逗号，特别允许使用中文逗号！\n[本行原始数据]\n{pprint.pformat(lineDict, sort_dicts=False)}'))
                else:
                    for keyStr in ('fieldName', 'fieldDescription'):
                        if keyStr in lineDict and lineDict[keyStr].strip() != '':
                            result.append(self.__buildDict('{0}#{1}{2}'.format(line_FieldID, keyStr, extraNumber),
                                                           lineDict[keyStr],
                                                           f'[本行原始数据]\n{pprint.pformat(lineDict, sort_dicts=False)}'))
        self.__writeParatranzJSON(result, args[1])

    def outLunaSettings(self, *args):
        # 读取内容
        with open(args[0], encoding='UTF-8') as tFile:
            result = list(csv.DictReader(tFile))
        tVar_data = self.__readParatranzJSON(args[1])
        for unit in tVar_data:  # 批量替换标签数据
            if 'tabValue$' in unit.key and unit.isTranslated:
                for line in result:
                    if 'tab' in line and line['tab'] == unit.original:
                        line['tab'] = self.__getTranslation(unit)
        for unit in tVar_data:
            if 'tabValue$' in unit.key:  # 不扫描特定数据
                continue
            csvKeyID, csvValueKeyID = unit.key.split('#')
            if '$' in csvValueKeyID:
                csvValueKeyID = csvValueKeyID.split('$')[0]  # 重复的键值会额外比较原文是否相符
                for line in result:
                    if line['fieldID'] == csvKeyID and line[csvValueKeyID] == unit.original:
                        if unit.isTranslated and len(self.__getTranslation(unit)) > 0:
                            line[csvValueKeyID] = self.__getTranslation(unit)
                            break
            else:
                for line in result:
                    if line['fieldID'] == csvKeyID:
                        if unit.isTranslated and len(self.__getTranslation(unit)) > 0:
                            line[csvValueKeyID] = self.__getTranslation(unit)
                            break
        with open(args[2], 'w', newline='', encoding='UTF-8') as tFile:
            tVar = csv.DictWriter(tFile, list(result[0].keys()))
            tVar.writeheader()
            tVar.writerows(result)

    # mod_info.json
    def inModInfo(self, *args):
        with open(args[0], encoding='UTF-8') as tFile:
            tOriginal: dict = json5.loads(self.__filterJSON5(tFile.read()))
        result = []
        hintBox = {'name': '本Mod的名称', 'description': '本Mod的描述'}
        for unitKey in hintBox:
            result.append(self.__buildDict(f'root#{unitKey}', tOriginal[unitKey], hintBox[unitKey]))
        self.__writeParatranzJSON(result, args[1])

    def outModInfo(self, *args):
        self.__commonTranslateFunc_v1(*args)

    # data/config/planets.json
    def inPlanets(self, *args):
        with open(args[0], encoding='UTF-8') as tFile:
            tOriginal: dict = json5.loads(self.__filterJSON5(tFile.read()))
        result = []
        for planetID in tOriginal:
            if 'name' in tOriginal[planetID]:
                result.append(
                    self.__buildDict(f'{planetID}#name', tOriginal[planetID]['name'], f'行星类型（{planetID}）的名称'))
        self.__writeParatranzJSON(result, args[1])

    def outPlanets(self, *args):
        self.__commonTranslateFunc_v2(*args)

    # data/config/settings.json
    # 240731: 仅处理 舰船设计分类 的颜色渲染效果，并尽可能使用较小影响的替换方式
    def inSettings(self, *args):
        from os.path import sep as os_sep, isfile, join as path_join
        from csv import DictReader

        with open(args[0], encoding='UTF-8') as tFile:
            tOriginal: dict = json5.loads(self.__filterJSON5(tFile.read()))
        result = []
        allDesignType = set()
        if 'designTypeColors' in tOriginal:
            for designType in tOriginal['designTypeColors']:  # 这串数据是字典，字符串映射到一串RGB值
                allDesignType.add(designType)
        # 调查所有涉及的文件
        mainFolderPath = str(args[0]).rpartition(os_sep)[0].rpartition(os_sep)[0]
        otherDesignType = set()
        for filePath in [('hullmods', 'hull_mods.csv'), ('hulls', 'ship_data.csv'), ('weapons', 'weapon_data.csv'),
                         ('campaign', 'special_items.csv')]:
            realFilePath = path_join(mainFolderPath, *filePath)
            if isfile(realFilePath):
                with open(realFilePath, encoding='UTF-8') as tFile:
                    for lineData in list(DictReader(tFile)):
                        if 'tech/manufacturer' in lineData:
                            tVar = lineData['tech/manufacturer']
                            if len(tVar.strip()) > 0:
                                otherDesignType.add(tVar.strip())
        for targetUnit in (otherDesignType & allDesignType):
            result.append(self.__buildDict(f'designTypeColors#{self.__simpleMD5(targetUnit)}', targetUnit,
                                           '要渲染的舰船/武器/船插/LPC的设计类型名称，比如 “扩展纪元”/“核心纪元”/“主宰纪元”'))
        self.__writeParatranzJSON(result, args[1])

    def outSettings(self, *args):
        with open(args[0], encoding='UTF-8') as tFile:
            tOriginal = tFile.read()
        for unit in self.__readParatranzJSON(args[1]):
            if unit.isTranslated:
                tOriginal = tOriginal.replace(f'"{unit.original}"', f'"{self.__getTranslation(unit)}"', 1)
        with open(args[2], 'w', encoding='UTF-8') as tFile:
            tFile.write(tOriginal)

    # data/config/battle_objectives.json
    def inBattleObjectives(self, *args):
        with open(args[0], encoding='UTF-8') as tFile:
            tOriginal: dict = json5.loads(self.__filterJSON5(tFile.read()))
        result = []
        for firstKey in tOriginal:
            if 'name' in tOriginal[firstKey]:
                result.append(self.__buildDict(f'{firstKey}#name', tOriginal[firstKey]['name'],
                                               f'[本行原始数据]\n{pprint.pformat(tOriginal[firstKey], sort_dicts=False)}'))
        self.__writeParatranzJSON(result, args[1])

    def outBattleObjectives(self, *args):
        self.__commonTranslateFunc_v2(*args)

    @staticmethod
    def __filterJSON5(fileContent: str):
        fileContent = fileContent.strip()
        if fileContent.endswith('},'):
            fileContent = fileContent[:-1]
        for number in range(10):
            if f'{number}f' in fileContent:
                fileContent = fileContent.replace(f'{number}f', str(number))
        tVar = []
        replace1 = re.compile('[^\\\\]",?[ \t]*#')  # strings.json定位
        replace2 = re.compile('(\\d|true|false|]|}|\\{|\\[),?[ \t]*#', re.IGNORECASE)  # 通用定位数据
        replace3 = re.compile(': *(TRUE|FALSE),?', re.IGNORECASE)
        for line in fileContent.splitlines():
            line = line.strip()
            if line.startswith('#') or len(line) == 0:
                continue
            elif replace1.search(line) is not None:
                toReplace = replace1.search(line).group()[1:]
                if ',' in toReplace:
                    line = line.replace(toReplace, '", //')
                else:
                    line = line.replace(toReplace, '" //')
            elif replace2.search(line) is not None:
                tStr = replace2.search(line).group()
                line = line.replace(tStr, tStr[:-1] + '//')
            if replace3.search(line) is not None:  # 给settings.json里讨人厌的代码纠错
                tStr = replace3.search(line).group()
                line = line.replace(tStr, tStr.lower())
            tVar.append(line)
        return '\n'.join(tVar)

    @staticmethod
    def __buildDict(keyID: str, original: str, context: str = None):
        return ParatranzDataUnit(keyID, original, context)

    @staticmethod
    def __writeParatranzJSON(content: List[ParatranzDataUnit], filePath: str):
        if len(content) == 0:
            return
        with open(filePath, 'w', encoding='UTF-8') as tFile:
            json.dump([x.asDict() for x in content], tFile, ensure_ascii=False, indent=4)

    @staticmethod
    def __readParatranzJSON(filePath: str) -> List[ParatranzDataUnit]:
        with open(filePath, encoding='UTF-8') as tFile:
            return [ParatranzDataUnit(**dataDict) for dataDict in json.load(tFile)]

    @staticmethod
    def __getTranslation(toGet: ParatranzDataUnit):
        return toGet.translation.replace('\\n', '\n')

    @staticmethod
    def __simpleMD5(toHashText: str):
        return md5(toHashText.encode('UTF-8')).hexdigest()

    def __commonTranslateFunc_v1(self, *args):
        """提供一些只有一层json的翻译函数。"""
        with open(args[0], encoding='UTF-8') as tFile:
            tOriginal: dict = json5.loads(self.__filterJSON5(tFile.read()))
        for unit in self.__readParatranzJSON(args[1]):
            if unit.isTranslated:
                keyStr = unit.key.split('#')[1]
                if keyStr in tOriginal:
                    tOriginal[keyStr] = self.__getTranslation(unit)
        with open(args[2], 'w', encoding='UTF-8') as tFile:
            json5.dump(tOriginal, tFile, ensure_ascii=False, indent=4, quote_keys=True)

    def __commonTranslateFunc_v2(self, *args):
        """2层json时使用。"""
        with open(args[0], encoding='UTF-8') as tFile:
            tOriginal: Dict[str, dict] = json5.loads(self.__filterJSON5(tFile.read()))
        for unit in self.__readParatranzJSON(args[1]):
            if unit.isTranslated:
                firstKey, secondKey = unit.key.split('#')
                if firstKey in tOriginal and secondKey in tOriginal[firstKey]:
                    tOriginal[firstKey][secondKey] = self.__getTranslation(unit)
        with open(args[2], 'w', encoding='UTF-8') as tFile:
            json5.dump(tOriginal, tFile, ensure_ascii=False, indent=4, quote_keys=True)

    @staticmethod
    def __extractDuplicateKeyText(toExtractDataList: List[dict], keyStr: str) -> Dict[str, int]:
        """提取重复的字符串以做集中处理，主要针对CSV文本ID。"""
        result = {}
        tVar = set()
        for unit in toExtractDataList:
            if [x.strip().startswith('#') for x in unit.values()].count(True) > 0:
                continue  # 检测到任意文本以注释符`#`开头，判定该行可能是注释，予以排除
            if keyStr in unit and unit[keyStr].strip() != '':
                if unit[keyStr] in tVar:
                    result[unit[keyStr]] = 1
                else:
                    tVar.add(unit[keyStr])
        return result

    @staticmethod
    def __quoteSpecialDataForIn(filterFunction: re.Pattern, preContent: str) -> str:
        """
        将配置文件中不用 **双引号** 括起来的非紧要关键字转成可以被正确处理的字符串。

        **仅可用于入方向，也就是将原始文件转为Paratranz数据文件的时候。**

        :param filterFunction: 过滤函数，用于在 **preContent** 中逐行查找匹配数据。
        :param preContent: 要处理的文本。
        :return: 已重新编码的数据。
        """
        preContentList = preContent.splitlines()
        const_searchEngine = re.compile('[A-Za-z0-9_.]+')
        const_referenceEngine = re.compile('"[A-Za-z0-9_.]+"')
        for lineID in range(len(preContentList)):
            if filterFunction.search(preContentList[lineID]) is not None:
                line = preContentList[lineID]
                headStr, _, line = line.partition(':')
                if '//' in line:
                    line, _, hintText = line.partition('//')
                else:
                    hintText = None
                line = line.strip()
                # 通过比较带引号的方式来处理文本
                t1 = const_searchEngine.findall(line)
                t2 = const_referenceEngine.findall(line)
                for t3 in t2:
                    if t3[1:-1] in t1:
                        t1.remove(t3[1:-1])
                # 预先移除不需要处理的词
                t4 = {}
                for needReplaceWord in t1:
                    str1, _, str2 = line.partition(needReplaceWord)
                    tMD5 = md5(str(len(t4)).encode()).hexdigest()
                    line = f'{str1}"{tMD5}"{str2}'
                    t4[tMD5] = needReplaceWord
                for unit in t4:
                    line = line.replace(unit, t4.get(unit))
                preContentList[lineID] = headStr + ':' + line + (f'//{hintText}' if hintText is not None else '')
        return '\n'.join(preContentList)

    @staticmethod
    def __quoteSpecialDataForOut(filterFunction: re.Pattern, preContent: str) -> Tuple[str, QuotedSpecialData]:
        """
        将配置文件中不用 **双引号** 括起来的非紧要关键字转成可以被正确处理的字符串。

        **仅可用于出方向，也就是将Paratranz数据文件转为已翻译文件的时候。**

        :param filterFunction: 过滤函数，用于在 **preContent** 中逐行查找匹配数据。
        :param preContent: 要处理的文本。
        :return: 已处理好的字符串 | 在之后提取时使用到的字符串集合。
        """
        preContentList = preContent.splitlines()
        const_searchEngine = re.compile('[A-Za-z0-9_.]+')
        const_referenceEngine = re.compile('"[A-Za-z0-9_.]+"')
        hashID = 1
        result = []
        for lineID in range(len(preContentList)):
            if filterFunction.search(preContentList[lineID]) is not None:
                line = preContentList[lineID]
                headStr, _, line = line.partition(':')
                if '//' in line:  # 直接删除注释
                    line = line.partition('//')[0]
                line = line.strip()
                # 通过比较带引号的方式来处理文本
                t1: List[str] = const_searchEngine.findall(line)
                t2 = const_referenceEngine.findall(line)
                for t3 in t2:
                    if t3[1:-1] in t1:
                        t1.remove(t3[1:-1])
                # 预先移除不需要处理的词
                if len(t1) > 0:
                    for needReplaceWord in t1:
                        str1, _, str2 = line.partition(needReplaceWord)
                        hashStr = md5(f'{hashID}'.encode()).hexdigest()
                        while hashStr in preContent:  # 使用非重复Hash进行标记
                            hashID += 1
                            hashStr = md5(f'{hashID}'.encode()).hexdigest()
                        line = f'{str1}"{hashStr}"{str2}'
                        result.append((f'"{hashStr}"', needReplaceWord))
                        hashID += 1
                    preContentList[lineID] = headStr + ':' + line
        return '\n'.join(preContentList), QuotedSpecialData(result)


if __name__ == '__main__':
    SubParatranz().Start()