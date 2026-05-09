# sensitive_filter.py - 敏感词过滤模块（DFA算法）
import re
from models import db, SensitiveWord

# 内置基础敏感词库
BUILTIN_WORDS = {
    # 联系方式类
    'contact': [
        '加微信', '加我微信', 'wx', 'wechat', '微信', '微信号', 'vx', 'v信',
        '加QQ', '扣扣', 'qq号', 'qq', 'q号', 'q q',
        '手机号', '手机', '电话', '打电话', '打给我', '发短信', '短信',
        '跳单', '私下', '转账', '收款', '红包', '支付宝', '银行卡',
        'TG', 'Telegram', 'telegram', '电报', '蝙蝠', 'signal',
        'WhatsApp', 'whatsapp', 'line', 'Line', 'skype', 'Skype'
    ],
    # 涉黄类
    'adult': [
        '做爱', '做a', '做ai', '性交', '约炮', '约p', '包夜', '出台',
        '丝袜', '裸聊', '裸视', '援交', '买春', '卖春', '一夜情',
        '色情', '黄色', '黄片', '黄图', 'av女', 'av男', 'a片',
        '看片', '资源', '上车', '老司机', '司机', '门一样的',
        '操', '肏', '干你', '草你', 'cnm', '艹', '日你', '尻'
    ],
    # 诈骗类
    'fraud': [
        '刷单', '兼职', '打字', '快递', '好评', '返利', '返现',
        '贷款', '借钱', '套现', '花呗', '借呗', '白条',
        '彩票', '博彩', '赌', '时时彩', 'pk10', '赛车',
        '投资', '理财', '炒股', '区块链', '虚拟币', '比特币',
        '赚钱', '日赚', '月入', '躺赚', '稳赚', '高返'
    ],
    # 竞品类
    'competitor': [
        '陌陌', '探探', 'soul', 'Soul', '积目', 'tt语音', '比心',
        'TT语音', '比心陪练', '陪我', 'TT陪玩', '连麦', '开黑',
        '同城', '附近', '夜场', '主播'
    ]
}

# 构建DFA状态机
class DFAFilter:
    def __init__(self):
        self.keywords = {}
        self.build_dict()

    def build_dict(self):
        """从内置词库构建DFA"""
        for category, words in BUILTIN_WORDS.items():
            for word in words:
                self.add_word(word)

    def add_word(self, word):
        """添加敏感词到DFA"""
        if not word:
            return
        tree = self.keywords
        for char in word:
            if char not in tree:
                tree[char] = {}
            tree = tree[char]
        tree[0] = 0  # 结束标记

    def check(self, text):
        """
        检查文本是否包含敏感词
        返回: (是否包含, 匹配到的第一个敏感词)
        """
        if not text:
            return False, None

        text = text.lower()

        for i in range(len(text)):
            word = self._detect(i, text)
            if word:
                return True, word

        return False, None

    def _detect(self, start, text):
        """从start位置开始检测"""
        tree = self.keywords
        word = []

        for i in range(start, len(text)):
            char = text[i]
            if char not in tree:
                break
            word.append(char)
            tree = tree[char]
            if 0 in tree:  # 匹配结束
                return ''.join(word)

        return None

    def replace(self, text, replace_char='*'):
        """替换敏感词为指定字符"""
        if not text:
            return text

        result = list(text)
        text_lower = text.lower()

        for i in range(len(text_lower)):
            word = self._detect(i, text_lower)
            if word:
                for j in range(len(word)):
                    if i + j < len(result):
                        result[i + j] = replace_char

        return ''.join(result)


# 全局过滤器实例
_filter = None

def get_filter():
    """获取或创建过滤器实例"""
    global _filter
    if _filter is None:
        _filter = DFAFilter()
        # 从数据库加载额外敏感词
        try:
            with db.session.begin_nested():
                db_words = SensitiveWord.query.all()
                for sw in db_words:
                    _filter.add_word(sw.word.lower())
        except Exception as e:
            print(f"加载数据库敏感词失败: {e}")
    return _filter


def check_content(content):
    """
    检查内容是否包含敏感词
    返回: (是否包含敏感词, 匹配到的敏感词)
    """
    f = get_filter()
    return f.check(content)


def filter_content(content, replace_char='*'):
    """过滤内容中的敏感词"""
    f = get_filter()
    return f.replace(content, replace_char)


def reload_filter():
    """重新加载过滤器（用于更新敏感词库后）"""
    global _filter
    _filter = None
    return get_filter()
