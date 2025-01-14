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