# 3. Read and score

All three pages were fetched and read on 2026-11-02. The score is a transparent editorial signal, not a claim about quality or traffic.

```text
python3 skills/research-first-writer/scripts/score_pages.py examples/faq-project/pages.json
```

| Page | Score | Coverage | Role |
|---|---:|---:|---|
| zapier.com/blog/best-project-management-software-small-business/ | 97.1 | 85% | current product-oriented benchmark |
| pmi.org/learning/library/guideline-evaluate-project-management-software-4629 | 67.4 | 85% | selection methodology and systems perspective |
| sba.gov/blog/2018/2018-06/checklist-choosing-business-software/ | 65.4 | 85% | small-business adoption and risk checklist |

Observed signals: search position was estimated from the three target queries; depth, structure, freshness, and author/source signals were read from each page. Public engagement counts and AI-citation data were not observable, so they are `null` in `pages.json` and excluded from the score. The Zapier page was updated in May 2026; the SBA and PMI pages show older publication dates, which is why freshness differs.

**Checkpoint 2:** Keep all three pages for analysis: they cover different jobs and are not duplicate product roundups.
