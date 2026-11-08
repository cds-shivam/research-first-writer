# 3. Read and score

तीन पृष्ठ और दो हिंदी PDF 2026-11-02 को खोले और पढ़े गए। `pages.json` में केवल पढ़े गए पृष्ठ शामिल हैं। स्कोर संपादकीय संकेत हैं, ट्रैफ़िक या गुणवत्ता का दावा नहीं।

```text
python skills/research-first-writer/scripts/score_pages.py examples/hindi-small-business-daily-routine/pages.json
```

| Page | Role | What was observable |
|---|---|---|
| taskee.pro/hi/solutions/small-and-medium-business/ | product benchmark | हिंदी में कार्य, समय-सीमा, सहयोग और Kanban भाषा |
| niesbud.nic.in/docs/Udyamita-Ebook.pdf | Indian authority | हिंदी उद्यमिता पाठ्यक्रम और व्यापार-योजना प्रश्न |
| rajshaladarpan.rajasthan.gov.in/.../11th_Employability_Skills_Hindi.pdf | local education context | हिंदी में लक्ष्य, समस्या-समाधान और व्यापार-योजना सामग्री |

Engagement और AI-citation signals दिखाई नहीं दिए; उन्हें `null` रखा गया और स्कोर में शामिल नहीं किया गया। Search position को इस छोटे, भाषा-विशिष्ट नमूने के लिए अनुमानित नहीं किया गया; `serp_rank` और `serp_coverage` को `null` रखा गया।

**Checkpoint 2:** तीन अलग भूमिकाएँ रखी गईं: उत्पाद पृष्ठ, भारतीय उद्यमिता स्रोत और स्थानीय शैक्षिक संदर्भ।
