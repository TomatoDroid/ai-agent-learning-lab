"""检查点 3.2：分块、BM25、RRF 与评测指标。运行：pytest tests/test_ch03_retrieval.py"""
import pytest

from mini_agent.retrieval import BM25Index, Hybrid, ToyDense, bm25_term, book_idf, chunk_text, hit_rate_at_k, lucene_idf, mrr, rrf, tokenize


def test_分词():
    assert tokenize("HTTP-403 错误") == ["http-403", "错误"]
    assert tokenize("退款流程") == ["退款", "款流", "流程"]


def test_分块_重叠与结尾():
    assert chunk_text("abcdefghij", 4, 1) == ["abcd", "defg", "ghij"]
    assert chunk_text("abcdefghijk", 4, 1) == ["abcd", "defg", "ghij", "jk"]
    assert chunk_text("abc", 4, 1) == ["abc"]
    assert chunk_text("", 4, 1) == []
    for size, overlap in [(4, 4), (4, -1), (0, 0)]:
        with pytest.raises(ValueError):
            chunk_text("abc", size, overlap)


@pytest.mark.parametrize("tf,df,dl,expected", [
    (5, 3, 200, 1.52), (2, 3, 500, 0.82), (8, 3, 150, 1.68),   # 词“模型”
    (3, 2, 200, 2.15), (1, 2, 250, 1.22),                      # 词“蒸馏”：更稀有，单次贡献更大
])
def test_BM25_复现原书实验3_5的日志(tf, df, dl, expected):
    assert bm25_term(tf, df, n=10, dl=dl, avgdl=250) == pytest.approx(expected, abs=0.01)


def test_BM25_词频饱和与常见词():
    assert bm25_term(10, 2, 10, 250, 250) < 2 * bm25_term(5, 2, 10, 250, 250), "出现 10 次不该是 5 次的两倍"
    assert book_idf(8, 10) == 0, "超过半数文档都有的词，IDF 取 0 而不是负数"
    assert bm25_term(3, 8, 10, 250, 250) == 0
    assert bm25_term(0, 2, 10, 250, 250) == 0


DOCS = {
    "refund": "退款政策：订单签收后7天内可申请全额退款，需提供订单号。",
    "refund_steps": "退款操作步骤：进入我的订单，选择订单，点击申请退款。",
    "cat": "Cat care guide: feeding, grooming and litter for your cat.",
    "dog": "Dog training basics: sit, stay and walk on a leash.",
    "e403": "HTTP-403 Forbidden 表示权限不足：检查 API Key 的权限范围。",
    "e500": "服务器错误的通用排查：查看日志、重启服务、检查依赖。",
}
CONCEPTS = {"kitty": "cat", "cat": "cat", "feline": "cat", "猫咪": "cat",
            "dog": "dog", "puppy": "dog",
            "退款": "refund", "refund": "refund",
            "错误": "error", "forbidden": "error", "报错": "error", "服务": "server", "服务器": "server", "务器": "server"}


def test_小语料上原书IDF会让常见词失效():
    docs = {"a": "特斯拉 保养", "b": "特斯拉 轮胎", "c": "邮寄 地址"}
    assert BM25Index(docs, idf=book_idf).search("特斯拉") == [], "3 篇里有 2 篇含这个词，IDF 被截成 0"
    assert [d for d, _ in BM25Index(docs).search("特斯拉")] == ["a", "b"]
    assert lucene_idf(2, 3) > 0


def test_倒排索引只为出现过的词建表():
    idx = BM25Index(DOCS)
    assert set(idx.postings["退款"]) == {"refund", "refund_steps"}
    assert idx.postings["退款"]["refund"] == 2
    assert idx.lengths["dog"] == len(tokenize(DOCS["dog"]))


def test_BM25检索_排序与截断():
    idx = BM25Index(DOCS)
    res = idx.search("退款 订单", k=5)
    assert [d for d, _ in res][:2] == ["refund", "refund_steps"] or [d for d, _ in res][:2] == ["refund_steps", "refund"]
    assert all(s > 0 for _, s in res) and res == sorted(res, key=lambda x: (-x[1], x[0]))
    assert idx.search("kitty") == [], "稀疏检索读不懂同义词"
    assert idx.search("HTTP-403")[0][0] == "e403", "稀疏检索精确匹配代码"
    assert len(idx.search("退款", k=1)) == 1


def test_RRF只看名次():
    fused = rrf([["a", "b", "c"], ["b", "d"]], k=60)
    assert fused[0][0] == "b"
    assert dict(fused)["b"] == pytest.approx(1 / 62 + 1 / 61)
    assert dict(fused)["d"] == pytest.approx(1 / 62)
    assert rrf([]) == []


def test_两路各有盲区_融合后都能找到():
    dense, sparse, hybrid = ToyDense(DOCS, CONCEPTS), BM25Index(DOCS), Hybrid(DOCS, CONCEPTS)
    rel = {"kitty": {"cat"}, "HTTP-403": {"e403"}, "退款怎么申请": {"refund", "refund_steps"}}

    def run(r):
        return {q: [d for d, _ in r.search(q, 3)] for q in rel}

    d, s, h = run(dense), run(sparse), run(hybrid)
    assert d["kitty"][0] == "cat" and s["kitty"] == []
    assert s["HTTP-403"][0] == "e403"
    assert hit_rate_at_k(h, rel, 1) == 1.0
    assert hit_rate_at_k(d, rel, 1) < 1.0 and hit_rate_at_k(s, rel, 1) < 1.0
    assert mrr(h, rel) >= max(mrr(d, rel), mrr(s, rel))


def test_评测指标():
    results = {"q1": ["x", "a"], "q2": ["b"], "q3": ["y", "z"]}
    rel = {"q1": {"a"}, "q2": {"b"}, "q3": {"c"}}
    assert hit_rate_at_k(results, rel, 1) == pytest.approx(1 / 3)
    assert hit_rate_at_k(results, rel, 2) == pytest.approx(2 / 3)
    assert mrr(results, rel) == pytest.approx((1 / 2 + 1 + 0) / 3)
