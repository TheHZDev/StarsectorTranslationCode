import pprint
from os import sep, scandir, DirEntry
from os.path import isfile, isdir
from typing import List, Dict
import re
import csv

import json
import json5

from para_tranz_script import PARA_TRANZ_PATH, ORIGINAL_PATH, TRANSLATION_PATH

PARA_TRANZ_PATH = str(PARA_TRANZ_PATH)
ORIGINAL_PATH = str(ORIGINAL_PATH)
TRANSLATION_PATH = str(TRANSLATION_PATH)


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
            if isinstance(program, dict) and program.get('Register') == 'mission' and len(self.__missionProgram) == 0:
                self.__missionProgram = program
            elif isinstance(program, dict) and 'FromOriginal' in program and 'ToLocalization' in program:
                tVar = program.get('Register')
                if tVar == 'path' and isinstance(program.get('Path'), list):
                    self.__pathProgram.append(program)
                elif tVar == 'folder' and isinstance(program.get('Folder'), list):
                    self.__folderProgram.append(program)
                elif tVar == 'ext' and isinstance(program.get('Ext'), list):
                    self.__extProgram.append(program)
                elif tVar == 'folder_ext' and isinstance(program.get('Folder_Ext'), list):
                    self.__folder_ext_Program.append(program)
                elif tVar == 'all':
                    self.__allProgram.append(program)

    def Start(self):
        print('Paratranz 项目助手', '1 - 从原始和汉化文件导出 ParaTranz 词条',
              '2 - 将 ParaTranz 词条写回汉化文件(localization)',
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


class SubParatranz(ParatrazProject):

    def ImportOneConfig(self, **kwargs):
        if kwargs.get('Register') == 'mission':
            self.Config.append({'Register': 'mission', 'FromMission': kwargs.get('FromMission').__name__,
                                'ToMission': kwargs.get('ToMission').__name__})
        else:
            fromOriginal = kwargs.get('FromOriginal')
            toLocalization = kwargs.get('ToLocalization')
            if callable(fromOriginal):
                fromOriginal = fromOriginal.__name__
            if callable(toLocalization):
                toLocalization = toLocalization.__name__
            if 'Register' not in kwargs or kwargs.get('Register') not in ('path', 'ext', 'folder', 'folder_ext', 'all'):
                return False
            if (kwargs.get('Register') == 'path' and not isinstance(kwargs.get('Path'), list)) or \
                    (kwargs.get('Register') == 'folder' and not isinstance(kwargs.get('Folder'), list)) or \
                    (kwargs.get('Register') == 'ext' and not isinstance(kwargs.get('Ext'), list)) or \
                    (kwargs.get('Register') == 'folder_ext' and not isinstance(kwargs.get('Folder_Ext'), list)):
                return False
            if not (isinstance(fromOriginal, str) and isinstance(toLocalization, str)):
                return False
            if not (callable(getattr(self, fromOriginal)) and callable(getattr(self, toLocalization))):
                return False
            # 开始动真格的
            thisConfig = {'Register': kwargs.get('Register'), 'FromOriginal': fromOriginal,
                          'ToLocalization': toLocalization}
            if kwargs.get('Register') == 'path':
                thisConfig['Path'] = kwargs.get('Path')
            elif kwargs.get('Register') == 'folder':
                thisConfig['Folder'] = kwargs.get('Folder')
            elif kwargs.get('Register') == 'ext':
                thisConfig['Ext'] = kwargs.get('Ext')
            elif kwargs.get('Register') == 'folder_ext':
                thisConfig['Folder_Ext'] = kwargs.get('Folder_Ext')
            self.Config.append(thisConfig)

    def ImportConfig(self):
        path = 'path'
        folder = 'folder'
        folder_ext = 'folder_ext'
        ext = 'ext'
        mission = 'mission'
        self.ImportOneConfig(Register=mission, FromMission=self.inMissions, ToMission=self.outMissions)
        # 原版 - 代码中的字符串外置文件
        self.ImportOneConfig(Register=path, Path=['/data/strings/strings.json'],
                             FromOriginal=self.inStringsJSON, ToLocalization=self.outStringsJSON)
        # 原版 - 势力相关配置文件
        self.ImportOneConfig(Register=folder_ext, Folder_Ext=[('/data/world/factions/', 'faction')],
                             FromOriginal=self.inFactions, ToLocalization=self.outFactions)
        # 原版 - 出现在S/L页面和主界面的游戏提示
        self.ImportOneConfig(Register=path, Path=['/data/strings/tips.json'],
                             FromOriginal=self.inTips, ToLocalization=self.outTips)
        # 战斗骚话mod - 相关战斗对话内容
        self.ImportOneConfig(Register=folder_ext, Folder_Ext=[('/data/config/chatter/characters/', 'json')],
                             FromOriginal=self.inChatter, ToLocalization=self.outChatter)
        # 势力争霸mod - 玩家可选的自定义开局
        self.ImportOneConfig(Register=path, Path=['/data/config/exerelin/customStarts.json'],
                             FromOriginal=self.inCustomStart, ToLocalization=self.outCustomStart)
        # 原版 - 默认阶层（Rank）相关配置
        self.ImportOneConfig(Register=path, Path=['/data/world/factions/default_ranks.json'],
                             FromOriginal=self.inDefaultRanks, ToLocalization=self.outDefaultRanks)
        # MagicLib mod - 高价值赏金（HVB）的相关内容
        self.ImportOneConfig(Register=path, Path=['/data/config/modFiles/magicBounty_data.json'],
                             FromOriginal=self.inMagicBountyData, ToLocalization=self.outMagicBountyData)
        # LunaLib mod - 一些用于在游戏中动态调整mod的数值的mod的相关配置
        self.ImportOneConfig(Register=path, Path=['/data/config/LunaSettings.csv'],
                             FromOriginal=self.inLunaSettings, ToLocalization=self.outLunaSettings)
        # 势力争霸mod - 势力建立同盟时的名称相关配置
        self.ImportOneConfig(Register=path, Path=['/data/config/exerelin/allianceNames.json'],
                             FromOriginal=self.inAllianceNames, ToLocalization=self.outAllianceNames)
        # 势力争霸mod - 势力间进行外交的相关配置（但主要是处理事件名称和描述）
        self.ImportOneConfig(Register=path, Path=['/data/config/exerelin/diplomacyConfig.json'],
                             FromOriginal=self.inDiplomacyConfig, ToLocalization=self.outDiplomacyConfig)
        # 势力争霸mod - 一个势力在势力争霸环境下所使用的舰队名称和其他特殊信息
        self.ImportOneConfig(Register=folder_ext, Folder_Ext=[('/data/config/exerelinFactionConfig/', 'json')],
                             FromOriginal=self.inExerelinFactionConfig, ToLocalization=self.outExerelinFactionConfig)
        # 星舰传奇mod - 目前只处理一个显示
        self.ImportOneConfig(Register=path, Path=['/data/config/starship_legends/factionConfigurations.json'],
                             FromOriginal=self.inFactionConfigurations, ToLocalization=self.outFactionConfigurations)
        # 原版 - 联络人的相关分类属性
        self.ImportOneConfig(Register=path, Path=['/data/config/contact_tag_data.json'],
                             FromOriginal=self.inContactTagData, ToLocalization=self.outContactTagData)
        # 原版 - 舰船具体配置文件
        self.ImportOneConfig(Register=folder_ext, Folder_Ext=[('/data/hulls/', 'ship')],
                             FromOriginal=self.inShipFile, ToLocalization=self.outShipFile)
        # 原版 - 舰船涂装配置
        self.ImportOneConfig(Register=folder_ext, Folder_Ext=[('/data/hulls/skins/', 'skin')],
                             FromOriginal=self.inHullSkinFile, ToLocalization=self.outHullSkinFile)
        # 工业革命mod - 宠物死因列表
        self.ImportOneConfig(Register=path, Path=['/data/strings/hamster_death_causes.csv', '/data/strings/combat_death_causes.csv'],
                             FromOriginal=self.inDeathCauses, ToLocalization=self.outDeathCauses)
        # 原版 - 自定义天体
        self.ImportOneConfig(Register=path, Path=['/data/config/custom_entities.json'],
                             FromOriginal=self.inCustomEntity, ToLocalization=self.outCustomEntity)

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
            if self.__hasTranslated(unit):
                if unit.get('key') == 'mission#text':
                    with open(args[4], 'w', encoding='UTF-8') as tFile:
                        tFile.write(self.__getTranslation(unit))
                else:
                    realID = unit.get('key').split('#')[1]
                    if realID in tContent:
                        tContent[realID] = self.__getTranslation(unit)
        with open(args[3], 'w', encoding='UTF-8') as tFile:
            json5.dump(tContent, tFile, ensure_ascii=False, indent=4, quote_keys=True)

    # data/strings/strings.json
    def inStringsJSON(self, *args):
        tFile = open(args[0], encoding='UTF-8')
        tFileContent = tFile.read()
        tFile.close()
        # 读取JSON
        commentCode = {}
        for line in tFileContent.splitlines():
            if '#' in line and '\"' in line:
                commentCode[line.split('\"')[1]] = line.strip().rpartition('#')[2]
            elif '//' in line and '\"' in line:
                commentCode[line.split('\"')[1]] = line.strip().rpartition('//')[2]
        # 解析注释完成
        originalJSON5: Dict[str, Dict[str, str]] = json5.loads(self.__filterJSON5(tFileContent))
        result = []
        for firstKey in originalJSON5.keys():
            for secondKey in originalJSON5.get(firstKey).keys():
                lineConfig = self.__buildDict(f'{firstKey}#{secondKey}', originalJSON5[firstKey][secondKey])
                if secondKey in commentCode:
                    lineConfig['context'] = commentCode.pop(secondKey)
                result.append(lineConfig)
        # 写入文件
        self.__writeParatranzJSON(result, args[1])

    def outStringsJSON(self, *args):
        tTranslation = self.__readParatranzJSON(args[1])
        # 读取内容
        result = {}
        for unit in tTranslation:
            keyID = unit.get('key', '').split('#')
            if keyID[0] not in result:
                result[keyID[0]] = {}
            if self.__hasTranslated(unit) and len(self.__getTranslation(unit)) > 0:
                result.get(keyID[0])[keyID[1]] = self.__getTranslation(unit)
            else:
                result.get(keyID[0])[keyID[1]] = unit.get('original')  # 不至于出现什么missing_string
        # 处理完成
        with open(args[2], 'w', encoding='UTF-8') as tFile:
            json5.dump(result, tFile, ensure_ascii=False, indent=4, quote_keys=True)

    # data/world/factions/*.faction
    def inFactions(self, *args):
        with open(args[0], encoding='UTF-8') as tFile:
            tFileContent: dict = json5.loads(self.__filterJSON5(tFile.read()))
        # 预定义关键字解析
        result = []
        for strKey in ('displayName', 'displayNameWithArticle', 'displayNameLong', 'displayNameLongWithArticle',
                       'displayNameIsOrAre'):
            if strKey in tFileContent:
                result.append(self.__buildDict(f'root#{strKey}', tFileContent.get(strKey)))
        # 名字好了
        if 'ranks' in tFileContent:
            ranksDict: Dict[str, Dict[str, Dict[str, str]]] = tFileContent.get('ranks')
            for firstKey in ranksDict.keys():
                for secondKey in ranksDict.get(firstKey).keys():
                    if 'name' in ranksDict.get(firstKey).get(secondKey):
                        result.append(self.__buildDict(f"ranks#{firstKey}#{secondKey}#name",
                                                       ranksDict.get(firstKey).get(secondKey).get('name')))
        # 阶级？
        if 'fleetTypeNames' in tFileContent:
            fleetNames: Dict[str, str] = tFileContent.get('fleetTypeNames')
            for firstKey in fleetNames.keys():
                result.append(self.__buildDict(f'fleetTypeNames#{firstKey}', fleetNames.get(firstKey)))
        self.__writeParatranzJSON(result, args[1])

    def outFactions(self, *args):
        with open(args[0], encoding='UTF-8') as tFile:
            tOriginal: dict = json5.loads(self.__filterJSON5(tFile.read()))
        # 读取原文文件内容
        tTranslation = self.__readParatranzJSON(args[1])
        # 读取译文文件内容
        for unit in tTranslation:
            if not self.__hasTranslated(unit):
                continue
            keyID: str = unit.get('key')
            translation: str = self.__getTranslation(unit)
            if len(translation) == 0:
                translation = unit.get('original')  # 确保始终有数据，不至于直接游戏中报错
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
            json5.dump(tOriginal, tFile, ensure_ascii=False, indent=4, quote_keys=True)

    # data/strings/tips.json
    def inTips(self, *args):
        tFile = open(args[0], encoding='UTF-8')
        tOriginal: dict = json5.loads(self.__filterJSON5(tFile.read()))
        tFile.close()
        # 读取原文文件内容
        result = []
        countID = 1
        for strUnit in tOriginal.get('tips'):
            if isinstance(strUnit, str):
                result.append(self.__buildDict(f'tips#{countID}', strUnit))
            elif isinstance(strUnit, dict):
                result.append(self.__buildDict(f'tips#{countID}${strUnit.get("freq")}', strUnit.get('tip')))
            countID += 1
        self.__writeParatranzJSON(result, args[1])

    def outTips(self, *args):
        tTranslation = self.__readParatranzJSON(args[1])
        result = {'tips': []}
        for unit in tTranslation:
            if self.__hasTranslated(unit):
                if '$' not in unit.get('key'):
                    result['tips'].append(self.__getTranslation(unit))
                else:
                    result['tips'].append(
                        {'freq': float(unit.get('key').split('$')[1]), 'tip': self.__getTranslation(unit)})
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
            if self.__hasTranslated(unit):
                firstKey = unit.get('key').split('$')[1].rpartition('@')[0]
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
            unitID = unit.get('key')
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
            if self.__hasTranslated(unit):
                unitID, unitKey = unit.get('key').split('#')
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
            if self.__hasTranslated(unit):
                firstKey, t1 = unit.get('key').split('#')
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
                self.__buildDict(f'event#{stageID}$name', eventUnit.get('name'), "外交事件：\n" + str(eventUnit)))
            result.append(
                self.__buildDict(f'event#{stageID}$desc', eventUnit.get('desc'), "外交事件：\n" + str(eventUnit)))
        self.__writeParatranzJSON(result, args[1])

    def outDiplomacyConfig(self, *args):
        with open(args[0], encoding='UTF-8') as tFile:
            tOriginal: dict = json5.loads(self.__filterJSON5(tFile.read()))
        tEvent: List[dict] = tOriginal['events']
        for unit in self.__readParatranzJSON(args[1]):
            if self.__hasTranslated(unit):
                stageID, unitKey = unit.get('key').split('#')[1].split('$')
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
            if self.__hasTranslated(unit):
                firstKey, tVar = unit.get('key').split('#')
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
        for bountyID in tOriginal:
            for paraName in ('job_name', 'job_description', 'job_comm_reply', 'job_intel_success', 'job_intel_failure',
                             'fleet_name', 'fleet_flagship_name'):
                if paraName in tOriginal[bountyID]:
                    result.append(self.__buildDict(f'{bountyID}#{paraName}', tOriginal[bountyID].get(paraName), f'[本行原始数据]\n{pprint.pformat(tOriginal[bountyID], sort_dicts=False)}'))
        self.__writeParatranzJSON(result, args[1])

    def outMagicBountyData(self, *args):
        self.__commonTranslateFunc_v2(*args)

    # data/config/exerelinFactionConfig/*.json
    def inExerelinFactionConfig(self, *args):
        toTranslateKeys = ('ngcTooltip', 'rebelFleetSuffix', 'asteroidMiningFleetName', 'gasMiningFleetName',
                           'invasionFleetName', 'responseFleetName', 'invasionSupportFleetName', 'defenceFleetName',
                           'suppressionFleetName', 'vengeanceLevelNames', 'vengeanceFleetNames', 'vengeanceFleetNamesSingle')
        with open(args[0], encoding='UTF-8') as tFile:
            tOriginal: dict = json5.loads(self.__filterJSON5(tFile.read()))
        result = []
        for translateKey in toTranslateKeys:
            if translateKey in tOriginal:
                if isinstance(tOriginal.get(translateKey), str):
                    result.append(self.__buildDict(translateKey, tOriginal.get(translateKey)))
                elif isinstance(tOriginal.get(translateKey), list):
                    for unitID in range(len(tOriginal.get(translateKey))):
                        if isinstance(tOriginal.get(translateKey)[unitID], str):
                            result.append(self.__buildDict(f'{translateKey}${unitID}', tOriginal.get(translateKey)[unitID]))
        self.__writeParatranzJSON(result, args[1])

    def outExerelinFactionConfig(self, *args):
        with open(args[0], encoding='UTF-8') as tFile:
            tOriginal: dict = json5.loads(self.__filterJSON5(tFile.read()))
        for unit in self.__readParatranzJSON(args[1]):
            if self.__hasTranslated(unit):
                if unit.get('key') in tOriginal:
                    tOriginal[unit.get('key')] = self.__getTranslation(unit)
                elif '$' in unit.get('key'):  # 单层数组替换操作
                    first, second = unit.get('key').split('$')
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
            result.append(self.__buildDict(f'root#hullName', tOriginal['hullName'], f'[本行原始数据]\n{pprint.pformat(tOriginal, sort_dicts=False)}'))
        self.__writeParatranzJSON(result, args[1])

    def outShipFile(self, *args):
        self.__commonTranslateFunc_v1(*args)

    # data/hulls/skins/*.skin
    def inHullSkinFile(self, *args):
        with open(args[0], encoding='UTF-8') as tFile:
            tOriginal: dict = json5.loads(self.__filterJSON5(tFile.read()))
        result = []
        for keyStr in ('hullName', 'descriptionPrefix'):
            if keyStr in tOriginal:
                result.append(self.__buildDict(f'root#{keyStr}', tOriginal[keyStr], f'[本行原始数据]\n{pprint.pformat(tOriginal, sort_dicts=False)}'))
        self.__writeParatranzJSON(result, args[1])

    def outHullSkinFile(self, *args):
        self.__commonTranslateFunc_v1(*args)

    # data/strings/combat_death_causes.csv 和 data/strings/hamster_death_causes.csv
    # 处理宠物系统的死因描述
    def inDeathCauses(self, *args):
        result = []
        with open(args[0], encoding='UTF-8') as tFile:
            textID = 1
            for line in list(csv.DictReader(tFile)):
                contextText = None
                if 'combat' in args[0]:
                    contextText = '该宠物在战斗中与被毁舰船一起共存亡了'
                elif 'hamster' in args[0]:
                    contextText = '这是一只hamster（仓鼠），自然死亡时的死因描述'
                result.append(self.__buildDict(f'id#{textID}', line['id'], contextText))
                textID += 1
        self.__writeParatranzJSON(result, args[1])

    def outDeathCauses(self, *args):
        result = []
        for unit in self.__readParatranzJSON(args[1]):
            if self.__hasTranslated(unit):
                result.append({'id': self.__getTranslation(unit)})
        with open(args[2], 'w', newline='', encoding='UTF-8') as tFile:
            tVar = csv.DictWriter(tFile, list(result[0].keys()))
            tVar.writeheader()
            tVar.writerows(result)

    # data/config/custom_entities.json
    def inCustomEntity(self, *args):
        with open(args[0], encoding='UTF-8') as tFile:
            preContent = self.__filterJSON5(tFile.read()).splitlines()
            for lineID in range(len(preContent)):
                lineStr = preContent[lineID].strip()
                if lineStr.startswith('//') or lineStr.startswith('#'):
                    continue
                if lineStr.startswith('"layers"'):
                    tVar = lineStr if '//' not in lineStr else lineStr.partition('//')[0]
                    # 预处理
                    tVar3 = tVar.replace('"layers"', '').replace(':', '').strip()
                    if tVar3.endswith(','):
                        tVar3 = tVar3[:-1]
                    tVar3 = tVar3.strip()
                    tVar2 = []
                    if ',' in tVar3:
                        for unit in tVar3.replace('[', '').replace(']', '').split(','):
                            tVar2.append(unit.strip())
                    else:
                        tVar2.append(tVar3[1:-1])
                    preContent[lineID] = lineStr.replace(tVar3, json.dumps(tVar2, ensure_ascii=False))
            tOriginal: dict = json5.loads('\n'.join(preContent))
        result = []
        for firstKey in tOriginal:
            secondDict: dict = tOriginal[firstKey]
            for unit in ('defaultName', 'nameInText', 'shortName', 'aOrAn', 'isOrAre'):
                if unit in secondDict:
                    result.append(self.__buildDict(f'{firstKey}#{unit}', secondDict[unit], f'[本行原始数据]\n{pprint.pformat(secondDict, sort_dicts=False)}'))
        self.__writeParatranzJSON(result, args[1])

    def outCustomEntity(self, *args):
        import hashlib, base64
        const_hash = hashlib.md5(args[0].encode('utf-8')).hexdigest()
        with open(args[0], encoding='UTF-8') as tFile:
            preContent = self.__filterJSON5(tFile.read()).splitlines()
            for lineID in range(len(preContent)):
                lineStr = preContent[lineID].strip()
                if lineStr.startswith('//') or lineStr.startswith('#'):
                    continue
                if lineStr.startswith('"layers"'): # 输出翻译时不需要考虑这行的内容，只需要之后输出后再替换回来就行
                    tVar = base64.b64encode((lineStr if '//' not in lineStr else lineStr.partition('//')[0]).strip().encode('UTF-8')).decode()
                    preContent[lineID] = f'"{const_hash}": "{tVar}"'
            tOriginal: dict = json5.loads('\n'.join(preContent))
        for unit in self.__readParatranzJSON(args[1]):
            if self.__hasTranslated(unit):
                firstKey, secondKey = unit.get('key').split('#')
                if firstKey in tOriginal:
                    tOriginal[firstKey][secondKey] = self.__getTranslation(unit)
        preResult: str = json5.dumps(tOriginal, ensure_ascii=False, indent=4, quote_keys=True)
        preResult_Group = preResult.splitlines()
        for lineID in range(len(preResult_Group)):
            lineStr = preResult_Group[lineID]
            if lineStr.strip().startswith(f'"{const_hash}"'):
                # 剥离出来后就可以替换掉了
                originalContent = base64.b64decode(lineStr.replace(const_hash, '').replace('"', '').replace(':', '').strip().encode()).decode('UTF-8')
                if not originalContent.endswith(','):
                    originalContent += ','
                preResult_Group[lineID] = originalContent
        with open(args[2], 'w', encoding='UTF-8') as tFile:
            tFile.write('\r\n'.join(preResult_Group))

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
                line_FieldID = lineDict['fieldID']
                extraNumber = ''
                if line_FieldID == '':
                    continue
                if lineDict['fieldType'] in ('Header', 'Text'):  # 检测到特殊头部信息
                    if line_FieldID in tVar1:  # 需要特别关照的重复键值将打上不同的ID，以便paratranz能认出来
                        extraNumber = f'${tVar1[line_FieldID]}'
                        tVar1[line_FieldID] += 1
                    result.append(
                        self.__buildDict(f'{line_FieldID}#defaultValue{extraNumber}', lineDict['defaultValue'],
                                         f'[本行原始数据]\n{pprint.pformat(lineDict, sort_dicts=False)}'))
                else:
                    for keyStr in ('fieldName', 'fieldDescription'):
                        if keyStr in lineDict and lineDict[keyStr].strip() != '':
                            if line_FieldID in tVar1:
                                extraNumber = f'${tVar1[line_FieldID]}'
                                tVar1[line_FieldID] += 1
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
            if 'tabValue$' in unit.get('key') and self.__hasTranslated(unit):
                for line in result:
                    if 'tab' in line and line['tab'] == unit.get('original'):
                        line['tab'] = self.__getTranslation(unit)
        for unit in tVar_data:
            if 'tabValue$' in unit.get('key'):  # 不扫描特定数据
                continue
            csvKeyID, csvValueKeyID = unit.get('key').split('#')
            if '$' in csvValueKeyID:
                csvValueKeyID = csvValueKeyID.split('$')[0]  # 重复的键值会额外比较原文是否相符
                for line in result:
                    if line['fieldID'] == csvKeyID and line[csvValueKeyID] == unit.get('original'):
                        if self.__hasTranslated(unit) and len(self.__getTranslation(unit)) > 0:
                            line[csvValueKeyID] = self.__getTranslation(unit)
                            break
            else:
                for line in result:
                    if line['fieldID'] == csvKeyID:
                        if self.__hasTranslated(unit) and len(self.__getTranslation(unit)) > 0:
                            line[csvValueKeyID] = self.__getTranslation(unit)
                            break
        with open(args[2], 'w', newline='', encoding='UTF-8') as tFile:
            tVar = csv.DictWriter(tFile, list(result[0].keys()))
            tVar.writeheader()
            tVar.writerows(result)

    @staticmethod
    def __filterJSON5(fileContent: str):
        fileContent = fileContent.strip()
        if fileContent.endswith('},'):
            fileContent = fileContent[:-1]
        for number in range(10):
            if f'{number}f' in fileContent:
                fileContent.replace(f'{number}f', str(number))
        tVar = []
        replace1 = re.compile('[^\\\\]",?[ \t]*#')  # strings.json定位
        replace2 = re.compile('(\\d|true|false|]|}|\[),?[ \t]*#')  # 通用定位数据
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
            tVar.append(line)
        return '\n'.join(tVar)

    @staticmethod
    def __buildDict(keyID: str, original: str, context: str = None):
        tVar = dict(key=keyID, original=original, translation="", stage=0)
        if context is not None:
            tVar['context'] = context
        return tVar

    @staticmethod
    def __writeParatranzJSON(content: list, filePath: str):
        if len(content) == 0:
            return
        tFile = open(filePath, 'w', encoding='UTF-8')
        json.dump(content, tFile, ensure_ascii=False, indent=4)
        tFile.close()

    @staticmethod
    def __readParatranzJSON(filePath: str) -> List[dict]:
        tFile = open(filePath, encoding='UTF-8')
        tData = json.load(tFile)
        tFile.close()
        return tData

    @staticmethod
    def __hasTranslated(toDetect: dict):
        if toDetect.get('stage') in (1, 3, 5):
            # 1 = 已翻译，3 = 已审核（一校），5 = 二校
            # 0 = 未翻译
            return True
        return False

    @staticmethod
    def __getTranslation(toGet: dict):
        return toGet.get('translation').replace('\\n', '\n')

    def __commonTranslateFunc_v1(self, *args):
        """提供一些只有一层json的翻译函数。"""
        with open(args[0], encoding='UTF-8') as tFile:
            tOriginal: Dict[str, dict] = json5.loads(self.__filterJSON5(tFile.read()))
        for unit in self.__readParatranzJSON(args[1]):
            if self.__hasTranslated(unit):
                keyStr = unit.get('key').split('#')[1]
                if keyStr in tOriginal:
                    tOriginal[keyStr] = self.__getTranslation(unit)
        with open(args[2], 'w', encoding='UTF-8') as tFile:
            json5.dump(tOriginal, tFile, ensure_ascii=False, indent=4, quote_keys=True)

    def __commonTranslateFunc_v2(self, *args):
        """2层json时使用。"""
        with open(args[0], encoding='UTF-8') as tFile:
            tOriginal: Dict[str, dict] = json5.loads(self.__filterJSON5(tFile.read()))
        for unit in self.__readParatranzJSON(args[1]):
            if self.__hasTranslated(unit):
                firstKey, secondKey = unit.get('key').split('#')
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
            if keyStr in unit and unit[keyStr].strip() != '':
                if unit[keyStr] in tVar:
                    result[unit[keyStr]] = 1
                else:
                    tVar.add(unit[keyStr])
        return result


if __name__ == '__main__':
    SubParatranz().Start()
