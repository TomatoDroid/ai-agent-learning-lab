"""检索：分块、BM25、混合检索与评测指标（练习 3.2）。

对应原书第三章“RAG 基础”与实验 3-5、3-6。
真实系统的稠密检索要用嵌入模型；这里用 ToyDense（一张手写的“同义概念表”）代替，
只为让你在离线测试里亲眼看到两路检索各自的盲区，以及融合为什么有用。
"""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Callable

STOPWORDS = {"的", "了", "是", "在", "和", "the", "a", "an", "of", "to", "is", "and", "for", "my", "我", "我的", "怎么", "如何"}

_TOKEN = re.compile(r"[a-z0-9]+(?:[-_.][a-z0-9]+)*|[一-鿿]+")


def tokenize(text: str) -> list[str]:
    """小写；英文和数字按词（"HTTP-403" 是一个词）；中文按相邻两字切分（“退款流程”→ 退款/款流/流程）。"""
    out: list[str] = []
    for m in _TOKEN.finditer(text.lower()):
        w = m.group()
        if "一" <= w[0] <= "鿿":
            out.extend([w] if len(w) == 1 else [w[i:i + 2] for i in range(len(w) - 1)])
        else:
            out.append(w)
    return [t for t in out if t not in STOPWORDS]


def chunk_text(text: str, size: int, overlap: int) -> list[str]:
    """按字符做固定大小分块，相邻块重叠 overlap 个字符。

    - 要求 0 <= overlap < size，否则抛 ValueError；
    - 第 i 块从 i * (size - overlap) 开始，长度最多 size；
    - 一旦某块已经到达文本末尾就停止（不要再产生一个被前一块完全包含的尾巴）；
    - 空文本返回 []。
    """
    # >>> EXERCISE 3.2a 固定大小分块
    # HINT: step = size - overlap；用 while 循环，start += step，块的结尾 end >= len(text) 时 break。
    if not 0 <= overlap < size:
        raise ValueError("need 0 <= overlap < size")
    chunks, start, step = [], 0, size - overlap
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start += step
    return chunks
    # <<< EXERCISE


def book_idf(df: int, n: int) -> float:
    """原书的 BM25 IDF：ln((n - df + 0.5) / (df + 0.5))，小于 0 时取 0（词出现在超过半数文档里时会变负）。"""
    # >>> EXERCISE 3.2b BM25 打分
    return max(0.0, math.log((n - df + 0.5) / (df + 0.5)))
    # <<< EXERCISE


def lucene_idf(df: int, n: int) -> float:
    """Lucene / Elasticsearch 的写法：ln(1 + (n - df + 0.5) / (df + 0.5))，永远为正。

    原书公式在大语料上没问题；但在用户记忆这种只有几十条的小语料上，一个词只要出现在一半文档里，
    IDF 就被截成 0，这个词等于没搜。所以 BM25Index 默认用这个版本。（本函数无练习。）
    """
    return math.log(1 + (n - df + 0.5) / (df + 0.5))


def bm25_term(tf: int, df: int, n: int, dl: int, avgdl: float, k1: float = 1.5, b: float = 0.75,
              idf: Callable[[int, int], float] = book_idf) -> float:
    """一个查询词对一篇文档的 BM25 贡献：idf(df, n) × 饱和后的词频。

    词频部分 = tf * (k1 + 1) / (tf + k1 * (1 - b + b * dl / avgdl))。tf 为 0 时返回 0。
    """
    # >>> EXERCISE 3.2b BM25 打分
    # HINT: 用原书实验 3-5 的日志验算：bm25_term(5, 3, 10, 200, 250) ≈ 1.52。
    if tf == 0:
        return 0.0
    return idf(df, n) * tf * (k1 + 1) / (tf + k1 * (1 - b + b * dl / avgdl))
    # <<< EXERCISE


class BM25Index:
    """稀疏检索：倒排索引 + BM25。"""

    def __init__(self, docs: dict[str, str], k1: float = 1.5, b: float = 0.75,
                 idf: Callable[[int, int], float] = lucene_idf):
        self.k1, self.b, self.idf = k1, b, idf
        self.docs = dict(docs)
        self.lengths: dict[str, int] = {}
        self.postings: dict[str, dict[str, int]] = {}  # 词 → {文档 id: 词频}
        # >>> EXERCISE 3.2b 建倒排索引
        # HINT: 对每篇文档 tokenize，lengths[id] = 词数；Counter 计词频后写进 postings[词][id]。
        for doc_id, text in self.docs.items():
            toks = tokenize(text)
            self.lengths[doc_id] = len(toks)
            for term, tf in Counter(toks).items():
                self.postings.setdefault(term, {})[doc_id] = tf
        # <<< EXERCISE
        self.avgdl = (sum(self.lengths.values()) / len(self.lengths)) if self.lengths else 0.0

    def search(self, query: str, k: int = 5) -> list[tuple[str, float]]:
        """返回得分最高的 k 个 (文档 id, 得分)，按得分降序、同分按 id 升序；得分为 0 的文档不返回。

        查询词重复出现只算一次（对查询分词后去重）。只需遍历查询词的倒排列表，不要扫描全部文档。
        """
        # >>> EXERCISE 3.2b BM25 检索
        # HINT: scores = Counter()；for term in set(tokenize(query)): for doc_id, tf in self.postings.get(term, {}).items(): ...
        # HINT: df 就是该词倒排列表的长度；调用 bm25_term 时传 idf=self.idf。
        scores: Counter = Counter()
        n = len(self.docs)
        for term in set(tokenize(query)):
            plist = self.postings.get(term, {})
            for doc_id, tf in plist.items():
                scores[doc_id] += bm25_term(tf, len(plist), n, self.lengths[doc_id], self.avgdl, self.k1, self.b, self.idf)
        ranked = sorted(((d, s) for d, s in scores.items() if s > 0), key=lambda x: (-x[1], x[0]))
        return ranked[:k]
        # <<< EXERCISE


class ToyDense:
    """稠密检索的替身：把词映射到“概念”，再算概念向量的余弦相似度。

    它懂同义（kitty、猫 → cat），但只认概念表里的词，所以读不出“HTTP-403”和“403”这种精确差别，
    这正是书中说的稠密检索的盲区。（本类无练习。）
    """

    def __init__(self, docs: dict[str, str], concepts: dict[str, str]):
        self.concepts = concepts
        self.vecs = {d: self._vec(t) for d, t in docs.items()}

    def _vec(self, text: str) -> Counter:
        return Counter(self.concepts[t] for t in tokenize(text) if t in self.concepts)

    def search(self, query: str, k: int = 5) -> list[tuple[str, float]]:
        q = self._vec(query)
        qn = math.sqrt(sum(v * v for v in q.values()))
        out = []
        for d, v in self.vecs.items():
            dn = math.sqrt(sum(x * x for x in v.values()))
            if qn and dn:
                s = sum(q[c] * v.get(c, 0) for c in q) / (qn * dn)
                if s > 0:
                    out.append((d, s))
        return sorted(out, key=lambda x: (-x[1], x[0]))[:k]


def rrf(rankings: list[list[str]], k: int = 60) -> list[tuple[str, float]]:
    """倒数排名融合：每个文档的得分 = Σ 1 / (k + 名次)，名次从 1 开始；某一路没出现就不加分。

    只看名次、不看原始得分，所以余弦（0~1）和 BM25（0~几十）可以直接融合。
    返回按得分降序、同分按 id 升序的 (id, 得分) 列表。
    """
    # >>> EXERCISE 3.2c RRF 融合
    # HINT: for ranking in rankings: for rank, doc_id in enumerate(ranking, start=1): scores[doc_id] += 1 / (k + rank)
    scores: Counter = Counter()
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking, start=1):
            scores[doc_id] += 1 / (k + rank)
    return sorted(scores.items(), key=lambda x: (-x[1], x[0]))
    # <<< EXERCISE


class Hybrid:
    """稠密 + 稀疏两路并行检索，RRF 融合。（本类无练习；重排序见“延伸”。）"""

    def __init__(self, docs: dict[str, str], concepts: dict[str, str], depth: int = 20):
        self.sparse = BM25Index(docs)
        self.dense = ToyDense(docs, concepts)
        self.depth = depth

    def search(self, query: str, k: int = 5) -> list[tuple[str, float]]:
        runs = [[d for d, _ in r.search(query, self.depth)] for r in (self.dense, self.sparse)]
        return rrf(runs)[:k]


def hit_rate_at_k(results: dict[str, list[str]], relevant: dict[str, set[str]], k: int) -> float:
    """书中所说的 recall@k（严格说是命中率）：前 k 个结果里至少有一个相关文档的查询所占比例。

    results: 查询 → 按名次排好的文档 id；relevant: 查询 → 相关文档集合。查询集合以 relevant 为准。
    """
    # >>> EXERCISE 3.2d 评测指标
    hits = sum(1 for q, rel in relevant.items() if rel & set(results.get(q, [])[:k]))
    return hits / len(relevant) if relevant else 0.0
    # <<< EXERCISE


def mrr(results: dict[str, list[str]], relevant: dict[str, set[str]]) -> float:
    """平均倒数排名：每个查询取第一个相关文档名次的倒数（没找到记 0），再对查询取平均。"""
    # >>> EXERCISE 3.2d 评测指标
    total = 0.0
    for q, rel in relevant.items():
        for rank, d in enumerate(results.get(q, []), start=1):
            if d in rel:
                total += 1 / rank
                break
    return total / len(relevant) if relevant else 0.0
    # <<< EXERCISE
