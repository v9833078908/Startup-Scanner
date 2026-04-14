# Pipeline v1 — 9-Stage Dual-Track Funnel

Пример прогона на данных DealPad от 13 апреля 2026.

## Воронка: 430 → 11

### [1/9] Parse DealPad
Берёт HTML-экспорт Telegram-канала DealPad. Каждое сообщение — стартап с именем, ссылкой, раундом, описанием. Парсит regex'ами, сохраняет в `1_ideas/` как Markdown с YAML frontmatter.

**Вход:** `messages.html` → **Выход:** 430 файлов `.md`

### [2/9] Pre-filter (LLM classification)
Gemini Flash классифицирует каждую идею: tech или нет, сектор, B2B/B2C, product_type. Hard-reject для явно нерелевантных (не tech, не софт, не наш сектор). Отсеянные уходят в `_archive/`.

**430 → ~325** (105 отсеяно)

### [3/9] Triage (маршрутизация)
LLM отвечает на бинарные вопросы по каждому стартапу:
- `has_product_evidence` — есть ли рабочий продукт?
- `has_founder_signal` — есть ли данные о фаундерах?
- `replicability` — можно ли повторить (easy/medium/hard)?
- `stack_fit` — подходит ли наш стек?
- `cis_gap_likelihood` — есть ли пустое место в СНГ?

По сумме сигналов считается **route**:
- `invest` — сильные фаундеры + продукт + раунд в диапазоне
- `build` — реплицируемо + stack_fit + CIS gap
- `both` — подходит обоим трекам
- `skip` — ни туда ни сюда

**325 → 20 build, 147 invest, 74 both, 84 skip**

Сейчас invest=off, include_both=on в конфиге → в research идут 94 (20 build + 74 both).

### [4/9] Invest Research — SKIP
Выключен в `config/triage.yaml` → `pipeline_tracks.invest: false`.

### [5/9] Build Research (DDG web search)
Для каждого из 20 стартапов делает 3 веб-поиска через DuckDuckGo:
- `"{категория} Россия"` — ищет CIS-конкурентов
- `"{категория} аналог CIS"` — альтернативы на рынке СНГ
- `"{имя} open source alternative github"` — OSS-базы

Результаты поиска (10 CIS + 5 OSS ссылок) скармливаются LLM, который синтезирует `build_research.md`: обзор категории, CIS-конкуренты, gap-анализ, OSS-альтернативы, оценка реплицируемости, рыночные сигналы, риски.

**20 → 20** (все получают research-файл)

### [6/9] Invest Gate — SKIP

### [7/9] Build Gate (контроль качества)
LLM читает build_research.md и отвечает на 5 вопросов (да/нет):
- CIS gap подтверждён?
- Реплицируемость подтверждена?
- Есть OSS-база?
- Есть сигналы спроса?
- Путь локализации понятен?

Формула прохождения: `cis_gap ИЛИ (replicable И market_demand)`

Смысл: не тратить дорогой Gemini Pro на стартапы, где web search не нашёл ничего полезного.

**20 → 11 ready, 9 filtered**

### [8/9] Deep Analysis (heavy model)
Gemini 2.5 Pro (~60 сек на стартап) делает полный анализ:
- **Invest scoring** — 10 критериев с весами (founder 20%, product 15%, traction 15%...)
- **Build scoring** — 8 критериев (market_opportunity 30%, ifree_fit 25%...)
- Вердикты: INVEST/WATCH/PASS для invest, BUILD/PARTNER/MONITOR/SKIP для build
- Развёрнутый текст: CIS adaptation, what to build, effort estimate

Записывает `3_analysis/{slug}_analysis.md`.

**11 → 11 analysis files**

### [9/9] Digest
Собирает все analysis-файлы, статистику pipeline, и генерирует еженедельный дайджест:
- Pipeline Summary (воронка числами)
- INVEST Candidates (score >= 8) — сейчас 0
- WATCH List (6-7.9) — 8 стартапов
- BUILD Opportunities (build >= 6) — 11 стартапов с рекомендациями
- Trends This Week
- All Scored Startups (таблица)

Сохраняет в `digests/2026-W16_weekly.md` и автокоммитит в git.

## Конфигурация

- **Треки:** `config/triage.yaml` — какие треки включены, пороги, маршрутизация
- **Скоринг:** `config/scoring_weights.yaml` — веса критериев для invest/build
- **Модели:** `.env` — OPENROUTER_MODEL_LIGHT (Flash), OPENROUTER_MODEL_HEAVY (Pro)
- **Промпты:** `prompts/` — отдельные файлы, не захардкожены в коде
- **Поиск:** SEARCH_BACKEND в `.env` — ddg (default), exa (quality), sonar (fallback)

## Метрики прогона (13 апреля 2026)

- Общее время: 590 сек (~10 мин)
- LLM вызовы: 787
- Prompt tokens: 828K
- Completion tokens: 151K
- Ошибки: 0
