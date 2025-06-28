import csv
import json
import hashlib
import shlex
import time
from os import sep as os_sep
import os.path
from typing import List

__lineBreakSymbol = '\r\n'
__rulesHeader = ('id', 'trigger', 'conditions', 'script', 'text', 'options', 'notes')


def makeBigBackspace(num: int = 1) -> str:
    return ' ' * 4 * num


def printFileHeader(**kwargs):
    """给java文件添加前置头数据。"""
    packageName = kwargs.get('package')  # java的类路径
    if packageName is None:
        outputFolder: str = kwargs.get('javaOutputFolder')
        if 'src' in outputFolder:
            t1 = outputFolder.split(f'{os_sep}src{os_sep}')[1]
            if t1.endswith(os_sep):
                t1 = t1.rstrip(os_sep)
            packageName = t1.replace(os_sep, '.')
    result = []
    if packageName is not None:
        result.append(f'package {packageName};')
    result += [
        '',
        'import com.fs.starfarer.api.Global;',
        'import com.fs.starfarer.api.SettingsAPI;',
        'import com.fs.starfarer.api.campaign.InteractionDialogAPI;',
        'import com.fs.starfarer.api.campaign.TextPanelAPI;',
        'import com.fs.starfarer.api.campaign.rules.MemoryAPI;',
        'import com.fs.starfarer.api.impl.campaign.rulecmd.BaseCommandPlugin;',
        'import com.fs.starfarer.api.util.Misc;',
        '',
        'import java.awt.*;',
        'import java.util.List;',
        'import java.util.Map;',
        '',
    ]
    return result


def printColorCode(*args):
    """整理颜色ID并输出为代码。"""
    result = []
    for colorStr in args:
        if colorStr == 'highlight':
            continue
        result.append(f'{colorStr} = globalSetting.getColor("{colorStr}")')
    return f'{makeBigBackspace(2)}Color {", ".join(result)};'


def printFileTail(**kwargs):
    """输出文件尾部数据。"""
    category = kwargs['stringsCategory']  # strings.json使用的第一层文本的名称
    javaClassName: str = kwargs['javaClassName']
    return [
        f'{makeBigBackspace(2)}return true;',
        f'{makeBigBackspace()}}}',
        '',
        f'{makeBigBackspace()}private String getString(String ID) {{',
        f'{makeBigBackspace(2)}return replaceToken(globalSetting.getString("{category}", String.format("{javaClassName}_%s", ID)));',
        f'{makeBigBackspace()}}}',
        '',
        # 250628：废弃旧高亮代码并向新的高亮代码过渡
        # f'{makeBigBackspace()}private String getString(int ID, int highlightID) {{',
        # f'{makeBigBackspace(2)}return replaceToken(globalSetting.getString("{category}", String.format("{javaClassName}_%d_highlight_%d", ID, highlightID)));',
        # f'{makeBigBackspace()}}}',
        f'{makeBigBackspace()}private String[] getHighlightsString(String ID){{',
        f'String t1 = replaceToken(globalSetting.getString("{category}", String.format("{javaClassName}_%s_highlights", ID)));',
        f'{makeBigBackspace(2)}if (t1.contains(" || ")) {{',
        f'{makeBigBackspace(3)}return t1.split(" \\\\|\\\\| ");',
        f'{makeBigBackspace(2)}}} else if (t1.contains("||")) {{',
        f'{makeBigBackspace(3)}return t1.split("\\\\|\\\\|");',
        f'{makeBigBackspace(2)}}} else {{',
        f'{makeBigBackspace(3)}return new String[]{{t1}};',
        f'{makeBigBackspace(2)}}}',
        f'{makeBigBackspace()}}}',
        '',
        f'{makeBigBackspace()}private String replaceToken(String source) {{',
        f'{makeBigBackspace(2)}return Global.getSector().getRules().performTokenReplacement(ruleId, source, dialog.getInteractionTarget(), memoryMap);',
        f'{makeBigBackspace()}}}',
        '}'
    ]

def printLog(msgText):
    print(msgText)


def mainFunc(**kwargs):
    """
    本函数用于解决 **Starsector** 游戏中的 **rules.csv** 中存在较长的高亮文本，由于中文版对高亮的支持不是很完善，导致长高亮文本换行后失去高亮的问题。

    通过将新增的文本设为高亮颜色，非高亮文本使用正常颜色进行高亮处理，即可在一定程度上解决该问题。该方案也被称为“反向高亮”。

    本函数需要一个 **rules.csv** 文件作为输入源，输出修改过的 **rules.csv** 文件、用于添加文本的 **Java** 代码文件以及外置了文本的 **strings.json** 文件。

    :keyword sourceFilePath: 源 **rules.csv** 文件的所在路径。
    :keyword javaClassName: 用于执行文本添加功能的 **java** 类的名称，请不要使用 **java** 编译器无法识别的字符串或与其他已有的 **BaseCommandPlugin** 相冲突的名称。
    :keyword stringsCategory: **strings.json** 中第一重字符串值的名称，不指定则使用随机名称。
    :keyword csvOutputFolder: 修改过的 **rules.csv** 的输出路径，不指定则输出到当前目录。
    :keyword javaOutputFolder: 执行文本添加功能的 **java** 源代码文件的输出路径，不指定则输出到当前目录。
    :keyword stringsOutputFolder: 外置文本所处的 **strings.json** 的输出路径，注意，它不会试图改写现有的文件！不指定则输出到当前目录。
    :keyword package: **java** 类的包名，可不指定。如果 **javaOutputFolder** 中包含 `src` 字样会尝试推测，你可能需要稍后自行修正java源码。
    :keyword addRulesHint: 布尔值，指定为 **True** 后会在修改后的 **rules.csv** 中的 `script` 列添加注释。
    :keyword addStringsHint: 布尔值，指定为 **True** 后会在 **strings.json** 中添加注释，以 JSON5 的格式存在。
    """
    csvOutputFolder: str = kwargs.get('csvOutputFolder', os.getcwd())  # 修改版的rules.csv输出文件路径
    stringsJSONOutputFolder: str = kwargs.get('stringsOutputFolder', os.getcwd())  # strings.json输出文件路径
    sourceRulesCSVFilePath: str = kwargs['sourceFilePath']  # rules.csv源文件路径
    addRulesHint: bool = kwargs.get('addRulesHint', False)
    addStringsHint: bool = kwargs.get('addStringsHint', False)
    stringsCategory: str = kwargs.get('stringsCategory', hashlib.md5(time.time().hex().encode('utf-8')).hexdigest())
    javaClassName: str = kwargs['javaClassName']  # java类名称
    javaOutputFolder: str = kwargs.get('javaOutputFolder', os.getcwd())  # java文件输出路径

    javaFileContent = printFileHeader(**kwargs)
    javaFileContent += [
        f'public class {javaClassName} extends BaseCommandPlugin {{',
        f'{makeBigBackspace()}private final SettingsAPI globalSetting = Global.getSettings();',
        f'{makeBigBackspace()}private String ruleId;',
        f'{makeBigBackspace()}private InteractionDialogAPI dialog;',
        f'{makeBigBackspace()}private Map<String, MemoryAPI> memoryMap;',
        '',
        f'{makeBigBackspace()}@Override',
        f'{makeBigBackspace()}public boolean execute(String ruleId, InteractionDialogAPI dialog, List<Misc.Token> params, Map<String, MemoryAPI> memoryMap) {{',
        f'{makeBigBackspace(2)}TextPanelAPI textPanel = dialog.getTextPanel();',
        f'{makeBigBackspace(2)}Color textColor = Misc.getTextColor(), highlight = Misc.getHighlightColor();',
        f'{makeBigBackspace(2)}this.ruleId = ruleId;',
        f'{makeBigBackspace(2)}this.dialog = dialog;',
        f'{makeBigBackspace(2)}this.memoryMap = memoryMap;',
        ''
    ]

    colorTextList = set()  # 记录颜色数据
    ruleIDs = []  # 记录ruleID数据
    switchHead, switchTail = f'{makeBigBackspace(2)}switch (ruleId) {{', f'{makeBigBackspace(2)}}}'
    switchCodes = []  # switch内部代码数据
    stringsData = {}  # 预备存入strings.json的数据
    ruleCountID = 1  # 统计用，也作为顺序ID使用

    with open(sourceRulesCSVFilePath, encoding='UTF-8', newline='') as csvFile:
        originalData = list(csv.DictReader(csvFile, __rulesHeader))

    for lineData in originalData:
        if lineData['script'] is None or lineData['text'] is None:  # 无需执行任何操作
            continue
        if 'SetTextHighlights' not in lineData['script'] or 'SetTextHighlightColors' not in lineData['script']:  # 文本没有高亮需求，略过
            continue
        scriptsText: List[str] = lineData['script'].splitlines()
        highlightColor: str = None
        highlightTexts: List[str] = []
        ruleID = lineData['id']
        ruleText = lineData['text']
        # tRegex1 = re.compile('" +"')
        # tRegex2 = re.compile('\\\\[A-Za-z0-9]')
        for scriptLine in scriptsText.copy():
            if scriptLine.strip().startswith('SetTextHighlightColors'):
                t1 = set(scriptLine.strip().replace('SetTextHighlightColors ', '').split())
                if len(t1) > 1:  # 多于1个的颜色不处理
                    printLog(f'检测到 {ruleID} 存在一个以上的高亮颜色，已略过。')
                    break
                highlightColor = t1.pop()
                scriptsText.remove(scriptLine)
            elif scriptLine.strip().startswith('SetTextHighlights'):
                t1 = scriptLine.strip().replace('SetTextHighlights ', '')
                highlightTexts = shlex.split(t1) # 250628：经由kimi分析后，我发现shlex的分割更好用
                scriptsText.remove(scriptLine)
        if highlightColor is None or len(highlightTexts) == 0:
            continue
        # 开始处理事情
        replaceToken = hashlib.md5(ruleText.encode('utf-8')).hexdigest()
        noHighlightText = lineData['text']
        for t2 in highlightTexts:
            noHighlightText = noHighlightText.replace(t2, replaceToken)
        noHighlightTexts = noHighlightText.split(replaceToken)
        for t2 in noHighlightTexts.copy():
            if t2.strip() == '':
                noHighlightTexts.remove(t2)
        if len(noHighlightTexts) == 0:  # 这说明整个文段都是高亮，不需要特别进行高亮处理
            switchCodes += [
                f'{makeBigBackspace(3)}case "{ruleID}":',
                f'{makeBigBackspace(4)}textPanel.addPara(getString("{ruleID}"), {highlightColor});',
                f'{makeBigBackspace(4)}break;'
            ]
            stringsData[f'{javaClassName}_{ruleID}'] = ruleText
        else:  # 处理一般情况
            colorTextList.add(highlightColor)  # 添加至高亮颜色数据库
            if '%' in ruleText:  # 防止高亮报错
                ruleText = ruleText.replace('%', '%%').replace('%%%%', '%%')
            stringsData[f'{javaClassName}_{ruleID}'] = ruleText.replace('\r\n', '\n')  # 把原始文本加入strings.json里
            highlightTextCode = []
            # hightlightID = 1
            for t3 in range(len(noHighlightTexts)):
                t2 = noHighlightTexts[t3].strip()
                if len(t2.splitlines()) > 1:  # 高亮文本内强制分段
                    for t5 in t2.splitlines():
                        if len(t5) > 0:  # 避免添加无意义换行符
                            highlightTextCode.append(t5)
                        # stringsData[f'{javaClassName}_{ruleID}_highlight_{hightlightID}'] = t5
                        # highlightTextCode.append(f'getString({ruleID}, {hightlightID})')
                        # hightlightID += 1
                else:
                    highlightTextCode.append(t2)
                    # stringsData[f'{javaClassName}_{ruleID}_highlight_{hightlightID}'] = t2
                    # highlightTextCode.append(f'getString({ruleID}, {hightlightID})')
                    # hightlightID += 1
            # t4 = ','.join(highlightTextCode)
            stringsData[f'{javaClassName}_{ruleID}_highlights'] = ' || '.join(highlightTextCode)
            switchCodes += [
                f'{makeBigBackspace(3)}case "{ruleID}":',
                f'{makeBigBackspace(4)}textPanel.addPara(getString("{ruleID}"), {highlightColor}, textColor, getHighlightsString("{ruleID}"));',
                f'{makeBigBackspace(4)}break;'
            ]
        scriptsText.append(javaClassName)
        if addRulesHint:
            scriptsText.append(f'# 文本被置换了，请参看 strings.json 中的 {stringsCategory}#{javaClassName}_{ruleID} 来了解 text 部分')
        ruleIDs.append(ruleID)
        ruleCountID += 1
        lineData['script'] = '\n'.join(scriptsText)
        lineData['text'] = None

    with open(os.path.join(csvOutputFolder, 'rules.csv'), 'w', encoding='UTF-8', newline='') as csvFile:
        tWriter = csv.DictWriter(csvFile, fieldnames=__rulesHeader)
        tWriter.writerows(originalData)

    with open(os.path.join(javaOutputFolder, f'{javaClassName}.java'), 'w', encoding='UTF-8') as javaFile:
        javaFileContent.append(printColorCode(*colorTextList))
        javaFileContent.append(switchHead)
        javaFileContent += switchCodes
        javaFileContent.append(switchTail)
        javaFileContent += printFileTail(**kwargs)
        javaFile.write('\n'.join(javaFileContent))

    with open(os.path.join(stringsJSONOutputFolder, 'strings.json'), 'w', encoding='UTF-8') as stringsFile:
        tempContents = json.dumps({stringsCategory: stringsData}, indent=4, ensure_ascii=False).splitlines()
        if addStringsHint:
            for lineID in range(len(tempContents)):
                if '_highlights' in tempContents[lineID]:
                    tempContents[lineID] += ' // 反向高亮文本'
                elif f'"{javaClassName}_' in tempContents[lineID]:
                    ruleID = tempContents[lineID].split(f'"{javaClassName}_')[1].split('"')[0]
                    tempContents[lineID] += f' // 对应rules.csv词条ID为 rules.csv#{ruleID}$text'
        stringsFile.write('\n'.join(tempContents))
