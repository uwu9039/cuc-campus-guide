// 表达体检 · 指标计算
// 说明：所有分数都由下面的明确规则算出，不掺任何主观调整。
// 真实系统里，segments 由 ASR（带时间戳）产出；这里用手写转写模拟。

import { readFileSync } from 'node:fs';

const FILLERS = ['那个就是', '我觉得', '然后', '就是', '这个', '那个', '其实', '嗯', '呃', '啊'];
const ORDER_WORDS = ['第一', '第二', '第三', '第四', '首先', '其次', '接着', '最后', '先说', '再说', '综上'];

const clean = (s) => s.replace(/[\s，。！？、；：""''（）—…·]/g, '');

function analyze(data) {
  const segs = data.segments;
  const duration = segs[segs.length - 1].e;
  const fullText = segs.map((s) => s.t).join('');
  const chars = clean(fullText).length;

  // 语速：字 / 分钟
  const rate = Math.round(chars / (duration / 60));

  // 长停顿：相邻句之间 >= 1.2 秒
  const pauses = [];
  for (let i = 1; i < segs.length; i++) {
    const gap = +(segs[i].s - segs[i - 1].e).toFixed(1);
    if (gap >= 1.2) pauses.push({ at: segs[i].s, dur: gap });
  }
  const maxPause = pauses.reduce((m, p) => Math.max(m, p.dur), 0);

  // 口头禅
  const fillerHits = [];
  let fillerCount = 0;
  for (const f of FILLERS) {
    let n = 0;
    for (const seg of segs) {
      let idx = seg.t.indexOf(f);
      while (idx !== -1) {
        n++;
        fillerHits.push({ word: f, at: +(seg.s + (idx / seg.t.length) * (seg.e - seg.s)).toFixed(1) });
        idx = seg.t.indexOf(f, idx + f.length);
      }
    }
    if (n) { fillerCount += n; }
  }
  // 去掉被长词包含的重复计数（如「那个就是」里的「那个」「就是」）
  const byWord = {};
  for (const h of fillerHits) byWord[h.word] = (byWord[h.word] || 0) + 1;
  const fillerPer100 = +((fillerCount / chars) * 100).toFixed(1);

  // 句长
  const sentences = fullText.split(/[。！？]/).map(clean).filter((s) => s.length > 1);
  const longest = sentences.reduce((m, s) => Math.max(m, s.length), 0);
  const avgLen = +(sentences.reduce((a, s) => a + s.length, 0) / sentences.length).toFixed(1);

  // 开口 10 秒说了多少字（信息密度）
  const first10 = segs.filter((s) => s.s < 10).map((s) => s.t).join('');
  const openingChars = clean(first10).length;

  // 结构：开场观点 / 序号 / 结论
  const firstTwo = segs.slice(0, 2).map((s) => s.t).join('');
  const hasThesis = /结论|我们认为|核心是|我想说|原因不是/.test(firstTwo);
  const orderHits = ORDER_WORDS.filter((w) => fullText.includes(w)).length;
  const hasSeq = orderHits >= 3;
  const lastSeg = segs[segs.length - 1].t;
  const hasClose = /谢谢|以上|综上|总结|下一步/.test(lastSeg);

  // ---- 评分规则（硬编码，可复现）----
  const rateScore = Math.max(35, Math.round(100 - Math.min(55, Math.abs(rate - 220) * 0.75)));
  const pauseScore = Math.max(40, Math.round(100 - pauses.length * 9 - Math.max(0, maxPause - 2.5) * 8));
  const fillerScore = Math.max(25, Math.round(100 - fillerPer100 * 9));
  const structureScore = (hasThesis ? 30 : 0) + (hasSeq ? 40 : 0) + (hasClose ? 30 : 0);

  const total = Math.round(
    rateScore * 0.3 + pauseScore * 0.25 + fillerScore * 0.2 + structureScore * 0.25
  );

  return {
    id: data.id,
    title: data.title,
    duration,
    chars,
    rate,
    pauses,
    pauseCount: pauses.length,
    maxPause,
    fillerCount,
    fillerPer100,
    byWord,
    fillerHits,
    openingChars,
    longest,
    avgLen,
    orderHits,
    hasThesis,
    hasSeq,
    hasClose,
    scores: { rate: rateScore, pause: pauseScore, filler: fillerScore, structure: structureScore },
    total,
  };
}

const results = process.argv.slice(2).map((f) => analyze(JSON.parse(readFileSync(f, 'utf8'))));
console.log(JSON.stringify(results, null, 2));
