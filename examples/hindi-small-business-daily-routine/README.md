# Example: छोटे व्यवसायों के लिए दैनिक दिनचर्या को व्यवस्थित करने के तरीके

यह Issue #11 के लिए भारत के हिंदी बाजार में किया गया in-market research run है। यह किसी अंग्रेज़ी लेख का अनुवाद नहीं है: queries, स्रोत-पठन, शोध-नोट्स और article हिंदी में बनाए गए।

- **Language / locale:** Hindi, `hi-IN`
- **Target market:** India
- **Keyword:** `छोटे व्यवसायों के लिए दैनिक दिनचर्या को व्यवस्थित करने के तरीके`
- **Intent:** informational FAQ
- **Research date:** 2026-11-02
- **Baselines:** Taskee Hindi product page, NIESBUD Hindi entrepreneurship handbook, Rajasthan Hindi vocational textbook
- **Important observation:** local results mix Hindi product copy with Indian educational material; vendor claims are treated as observations, not proof.
- **Limitation:** search rankings, traffic, and first-hand product usage were not claimed. A human should review Hindi register and supply the image slot.

| Stage | File | Result |
|---|---|---|
| Brief | [01-brief.md](01-brief.md) | Language, market, audience, and evidence boundaries |
| Discover | [02-discover.md](02-discover.md) | Hindi queries and local result types |
| Read and score | [03-scores.md](03-scores.md), [pages.json](pages.json) | Three fetched pages/PDFs and observable signals |
| Analyse | [04-analysis.md](04-analysis.md) | Local-language angles, gaps, and short quotes |
| Baselines | [05-baselines.md](05-baselines.md) | One role per baseline |
| Research brief | [06-research-brief.md](06-research-brief.md) | Hindi must-covers and facts ledger |
| Outline | [07-outline.md](07-outline.md) | Five answer-first FAQ questions |
| Write and review | [article.md](article.md), [review-report.md](review-report.md) | Article and language-check findings |

The checker change is documented in `review-report.md`: Unicode word counting is fixed, while English readability and stock-phrase checks are explicitly marked not applicable for predominantly non-Latin text.
