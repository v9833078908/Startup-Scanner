# Система скаутинга стартапов и идей
## 4 дня до работающего pipeline — полное руководство

---

# Часть 1. Контекст и задача

## Кто мы и что нам нужно

**iFree** — технологическая компания (не фонд), которая хочет запустить инвестиционную активность и параллельно находить идеи для собственных продуктов.

**Параметры инвестиций:**
- Чек: $30K — $300K за сделку
- Стадия: seed / ранний рост
- Воронка: ~30 стартапов → 1–2 инвестиции
- Фокус: AI, финтех, геймдев, developer tools, инфраструктура, автоматизация
- География: Россия + глобал
- Главный фильтр: **сильные фаундеры** — команда важнее идеи

**Параметры поиска собственных идей:**
- Горячие ниши, где есть traction, но нет доминирующего игрока
- Open-source проекты с тысячами stars, которые можно коммерциализировать (типа Semaphore — классный продукт, непонятно что с ним делать бизнесово)
- Паттерны из YC-батчей: во что инвестирует YC → что можно сделать самим или адаптировать для российского / B2B рынка
- Продукты, которые можно cross-sell через существующих клиентов группы iFree

**Два режима работы системы:**
1. **Invest mode** — найти стартап, оценить, проинвестировать
2. **Build mode** — найти горячую нишу / идею / open-source проект, собрать команду, сделать продукт самим

Оба режима питаются из одного потока данных, но анализируются по-разному.

## Почему именно сейчас

Российский венчурный рынок сломан: нет цепочки exit → IPO, высокая ставка, инвесторы в дивидендах. Но это создаёт возможность: конкуренция за сделки минимальна, оценки ниже, сильные технари продолжают строить. Open-source проекты из России — недооценены.

На глобале: YC выпускает 200 стартапов за батч, Product Hunt — десятки запусков в день, GitHub trending — постоянный поток. Проблема не в отсутствии стартапов, а в том, чтобы найти правильные.

## Инвестиционный тезис

Ищем:
- Технологические компании с сильным техническим фаундером
- В областях: AI/ML, финтех, геймдев, developer tools, инфраструктура, автоматизация
- Которые понимают масштаб (не lifestyle-бизнес)
- С которыми iFree может дать value beyond money: аудитория, B2B-контакты, cross-sell
- Open-minded фаундеры, не привязанные к одному рынку

**Три потока входящих:**
1. **Автоматический скаутинг** — парсинг источников (то, что строим)
2. **Сверху** — обмен dealflow с фондами и синдикатами
3. **Из окружения** — warm intros от доверенных людей

---

# Часть 2. Архитектура: три папки

## Суть

Git-репозиторий с тремя папками и набор скриптов. Никаких баз данных, фреймворков, деплоя на серверы. Всё в Markdown, всё под версионным контролем.

```
scouting-pipeline/
├── README.md
├── THESIS.md                    # Инвестиционный тезис и критерии
├── TEMPLATE_idea.md
├── TEMPLATE_profile.md
├── TEMPLATE_analysis.md
│
├── 1_ideas/                     # ВХОД: сырые находки от всех парсеров
│   ├── 2025-04-01_codeweave.md
│   ├── 2025-04-02_semaphore.md
│   └── ...
│
├── 2_research/                  # СЕРЕДИНА: собранная информация
│   ├── codeweave/
│   │   ├── profile.md
│   │   ├── founders.md
│   │   ├── github_metrics.md
│   │   ├── website_content.md
│   │   ├── social_mentions.md
│   │   └── raw/
│   └── ...
│
├── 3_analysis/                  # ВЫХОД: заключения, скоринг, рекомендации
│   ├── codeweave_analysis.md
│   └── ...
│
├── _archive/                    # Отклонённые
│
├── digests/                     # Сгенерированные дайджесты и отчёты
│   ├── 2025-04-15_daily.md
│   ├── 2025-W16_weekly.md
│   ├── 2025-04_trends.md
│   └── ...
│
├── scouts/                      # ВСЕ парсеры-скауты
│   ├── base_scout.py
│   ├── github_trending.py
│   ├── github_repo_metrics.py
│   ├── hackernews.py
│   ├── producthunt.py
│   ├── reddit.py
│   ├── telegram_channels.py
│   ├── yc_companies.py
│   ├── vc_ru.py
│   ├── habr.py
│   ├── indie_hackers.py
│   ├── rss_feeds.py
│   ├── betalist.py
│   └── founder_tracker.py
│
├── research/                    # Скрипты сбора информации
│   ├── enrich_github.py
│   ├── enrich_website.py
│   ├── enrich_mentions.py
│   ├── convert_to_md.py
│   ├── move_to_research.py
│   └── research_agent.py
│
├── analysis/                    # Скрипты анализа и генерации output
│   ├── analyze_startup.py       # Invest-mode анализ
│   ├── analyze_idea.py          # Build-mode анализ
│   ├── scoring.py
│   ├── daily_digest.py
│   ├── weekly_report.py
│   ├── trends_report.py
│   └── build_opportunities.py   # Отчёт по идеям для собственных продуктов
│
├── scripts/
│   ├── run_all_scouts.sh
│   ├── status.py
│   ├── move_old_ideas.py
│   └── full_pipeline.py
│
└── config/
    ├── sources.yaml
    ├── telegram_channels.yaml
    ├── scoring_weights.yaml
    ├── tracked_founders.yaml
    └── .env
```

## Поток данных

```
15 ПАРСЕРОВ                      1_IDEAS              2_RESEARCH              3_ANALYSIS
──────────────                   ──────               ──────────              ──────────
GitHub Trending    ─┐
GitHub Metrics     ─┤
Hacker News        ─┤
Product Hunt       ─┤            ┌─────────┐         ┌──────────┐           ┌───────────┐
Reddit (3 sub)     ─┤            │ MD-файл │         │ Папка с  │           │Заключение │
Telegram (5 кан)   ─┼─ скрипты ─>│ на каждый│──(пауза)─>│ данными  │──агент──>│ за/против │
YC Companies       ─┤            │ стартап  │  + чел. │ по стар- │  Claude  │ скоринг   │
vc.ru              ─┤            │          │ решает  │ тапу     │          │ что делать│
Habr               ─┤            └─────────┘         └──────────┘          └───────────┘
Indie Hackers      ─┤                                                            │
RSS feeds          ─┤                                                            ▼
Betalist           ─┤                                                    ┌───────────────┐
Founder tracker    ─┘                                                    │   DIGESTS/    │
                                                                         │ Daily digest  │
Warm intros ───── руками в 1_ideas                                       │ Weekly report │
Dealflow    ───── руками в 1_ideas                                       │ Trend report  │
                                                                         │ Build ideas   │
                                                                         └───────────────┘
```

---

# Часть 3. Все источники — сразу

## Полный список парсеров (15 штук, все с первого дня)

### Глобальные

| # | Парсер | Источник | Что извлекаем | Частота | Сложность |
|---|--------|---------|--------------|---------|-----------|
| 1 | `github_trending.py` | github.com/trending | Trending repos daily/weekly, stars, language | 2x/день | Лёгкая (scraping) |
| 2 | `github_repo_metrics.py` | GitHub API | Stars velocity, forks, contributors, commits для отслеживаемых repos | 1x/день | Лёгкая (API) |
| 3 | `hackernews.py` | HN Firebase API | Show HN, Launch HN, top stories с URL на стартапы | 4x/день | Лёгкая (API) |
| 4 | `producthunt.py` | Product Hunt | Top launches, upvotes, makers, topics | 1x/день | Средняя (GraphQL API) |
| 5 | `reddit.py` | Reddit JSON API | r/SaaS, r/startups, r/MachineLearning, r/selfhosted | 2x/день | Лёгкая (JSON) |
| 6 | `yc_companies.py` | ycombinator.com/companies | Batch companies, описания, verticals | 1x/неделю | Средняя (scraping) |
| 7 | `indie_hackers.py` | indiehackers.com | Revenue milestones, launches | 1x/день | Средняя (scraping) |
| 8 | `rss_feeds.py` | TechCrunch, Sifted, Crunchbase News | Funding rounds, launches, news | 2x/день | Лёгкая (RSS) |
| 9 | `betalist.py` | betalist.com | Beta launches | 1x/день | Лёгкая (RSS/scraping) |

### Русскоязычные

| # | Парсер | Источник | Что извлекаем | Частота | Сложность |
|---|--------|---------|--------------|---------|-----------|
| 10 | `telegram_channels.py` | 5+ каналов | Посты с URL и ключевыми словами | 3x/день | Средняя (Telethon) |
| 11 | `vc_ru.py` | vc.ru RSS | Статьи про стартапы, launches | 2x/день | Лёгкая (RSS) |
| 12 | `habr.py` | Habr API | Tech-статьи, open-source проекты | 1x/день | Лёгкая (API) |

### Специальные

| # | Парсер | Источник | Что извлекаем | Частота | Сложность |
|---|--------|---------|--------------|---------|-----------|
| 13 | `founder_tracker.py` | GitHub + config | Новые repos и activity отслеживаемых фаундеров | 1x/день | Лёгкая (API) |
| 14 | `yc_lookalike.py` | GitHub Search | Repos похожие на YC-компании текущего батча | 1x/неделю | Средняя |
| 15 | `chrome_extensions.py` | Chrome Web Store | Новые расширения в категориях productivity/developer | 1x/неделю | Средняя |

### Telegram-каналы (config)

```yaml
# config/telegram_channels.yaml
channels:
  - username: "productradar"
    name: "Product Radar"
    keywords: ["запуск", "стартап", "продукт", "launched", "seed", "raised", "open source"]
  - username: "the_edinorog"
    name: "The Edinorog"
    keywords: ["стартап", "инвестиц", "раунд", "фаундер", "exit"]
  - username: "startupoftheday"
    name: "Стартап дня"
    keywords: []  # все посты
  - username: "rusbase"
    name: "Rusbase"
    keywords: ["стартап", "раунд", "инвестиц", "запуск"]
  - username: "apptractor"
    name: "AppTractor"
    keywords: ["приложение", "запуск", "продукт", "AI"]
```

### RSS-ленты (config)

```yaml
# В config/sources.yaml, секция rss_feeds
feeds:
  - url: "https://techcrunch.com/feed/"
    name: "TechCrunch"
    keywords: ["startup", "seed", "series a", "raised", "launch", "AI"]
  - url: "https://feeds.feedburner.com/crabortnews"
    name: "Crunchbase News"
    keywords: ["funding", "raised", "seed", "series"]
  - url: "https://sifted.eu/feed"
    name: "Sifted"
    keywords: ["startup", "raised", "launch"]
  - url: "https://vc.ru/rss/all"
    name: "vc.ru"
    keywords: ["стартап", "запуск", "привлёк", "раунд", "инвестиц"]
```

---

# Часть 4. Двойной режим: Invest + Build

## Invest Mode — найти стартап для инвестиции

Классический скаутинг: находим стартап → собираем данные → анализируем → принимаем решение об инвестиции.

**Ключевые вопросы анализа:**
- Насколько сильный фаундер?
- Есть ли traction?
- Подходит ли наш чек ($30–300K)?
- Можем ли дать value (контакты, аудитория, cross-sell)?
- Каков потенциал exit?

## Build Mode — найти идею для собственного продукта

Система анализирует поток и выделяет возможности для iFree:

**Паттерн 1: «YC-тренды → российская адаптация»**
- YC инвестирует в 15 стартапов в категории X → эта ниша горячая
- Если в России нет аналога → можно делать самим
- Пример: YC W25 — 8 стартапов в AI code review → в России этого нет → opportunity

**Паттерн 2: «Open-source с звёздами, но без бизнеса»**
- GitHub trending repo с 10K+ stars, active development, но нет компании/revenue
- Можно: white-label, managed hosting, enterprise версия, вертикальная адаптация
- Пример: Semaphore — классный Ansible UI, десятки тысяч звёзд, непонятно что с бизнесом

**Паттерн 3: «Hot product + iFree's audience = cross-sell»**
- Новый B2B-продукт набирает traction
- У iFree есть клиенты, которым это может быть нужно
- Можно: партнёрство, white-label, или свой аналог для своей аудитории

**Паттерн 4: «Горячая ниша, нет доминирующего игрока»**
- Несколько стартапов в одной нише, все маленькие, рынок растёт
- Значит ниша реальная, но лидера ещё нет → можно зайти

## Разница в анализе

| Аспект | Invest Mode | Build Mode |
|--------|------------|------------|
| Ключевой вопрос | «Стоит ли вложить $30–300K?» | «Стоит ли делать это самим?» |
| Фокус на фаундере | Критичен (20% скоринга) | Не важен (мы сами фаундеры) |
| Фокус на рынке | Важен (10%) | Критичен (30%) |
| Фокус на iFree fit | Приятный бонус (10%) | Ключевой фактор (30%) |
| Output | «INVEST / WATCH / PASS» | «BUILD / PARTNER / MONITOR / SKIP» |

---

# Часть 5. Скоринг

## Invest Mode Scoring (10 критериев, 1–10)

| Критерий | Вес | Что оцениваем |
|----------|:---:|--------------|
| **Сила фаундеров** | 20% | Опыт, exits, техническая глубина, адекватность |
| **Продукт** | 15% | Работает ли, UX, техническое качество |
| **Traction** | 15% | Пользователи, revenue, рост, engagement |
| **Рынок** | 10% | TAM, конкуренция, timing |
| **Бизнес-модель** | 10% | Как зарабатывает, unit economics |
| **Технология** | 10% | Сложность, moat, IP |
| **Fit с iFree** | 10% | Можем ли дать value, synergy с бизнесом |
| **Momentum** | 5% | Скорость роста за последний месяц |
| **Fundraising fit** | 3% | Подходит ли чек, стадия, условия |
| **Gut feeling** | 2% | Интуиция |

Результат: **INVEST** (≥8) / **WATCH** (6–7.9) / **PASS** (<6)

## Build Mode Scoring (8 критериев, 1–10)

| Критерий | Вес | Что оцениваем |
|----------|:---:|--------------|
| **Market opportunity** | 30% | Размер ниши, рост, наличие конкурентов, timing |
| **iFree fit** | 25% | Cross-sell с аудиторией, имеющиеся компетенции, ресурсы |
| **Technical feasibility** | 15% | Можем ли мы это построить (есть ли open-source база, сколько это стоит) |
| **Speed to market** | 10% | Как быстро можно запустить MVP |
| **Revenue potential** | 10% | Как быстро можно начать зарабатывать |
| **Defensibility** | 5% | Можно ли удержать позицию (data moat, network effects, brand) |
| **Trend alignment** | 3% | Насколько это в тренде (YC, VC interest, media buzz) |
| **Gut feeling** | 2% | Интуиция |

Результат: **BUILD** (≥8) / **PARTNER** (6–7.9) / **MONITOR** (4–5.9) / **SKIP** (<4)

---

# Часть 6. Артефакты на выходе

Это главная часть. Система ценна не парсингом, а тем, что она **производит** — конкретные документы, которые можно читать, обсуждать, действовать по ним.

## 6.1. Daily Digest

**Когда:** каждое утро, автоматически
**Для кого:** Дина + команда, быстрый обзор за 3 минуты
**Формат:** Markdown файл в `digests/` + отправка в Telegram/email

---

### Пример Daily Digest

```markdown
# 🔍 Scouting Digest — 15 апреля 2025, вторник

> Pipeline: 47 ideas → 12 in research → 8 analysed
> Новых за 24ч: 11 идей из 9 источников

---

## 🔥 Горячее: что нельзя пропустить

### 1. Luminous AI — AI-агент для финансового анализа
- **Score: 8.4 / 10** → ⚡ INVEST CANDIDATE
- **Источники:** Show HN (#1, 487 pts) + Product Hunt (#2, 1,240 upvotes) + Telegram: Edinorog
- **Фаундер:** Dmitry Volkov — ex-Goldman Sachs VP (8 лет), CFA, prev. co-founder DataBridge (acquired 2022 ~$5M)
- **Traction:** 2,100 stars на GitHub за 5 дней, waitlist 4,000+
- **Стадия:** Pre-seed, ищут $500K (наш чек проходит)
- **Почему горячий:** Тройное совпадение источников за 48ч + сильный финтех-фаундер + наш тезис (AI + fintech)
- **→ Рекомендация: связаться в течение 48 часов**

### 2. Infractl — open-source платформа для управления cloud-инфраструктурой
- **Score: 7.8 / 10** → 👀 WATCH
- **Источники:** GitHub Trending #3 (weekly) + Reddit r/selfhosted (340 upvotes)
- **Фаундер:** Неизвестен, нужен ресерч
- **Traction:** 8,700 stars (↑2,100 за неделю), 89 contributors, issue response <2ч
- **Стадия:** Нет компании, только open-source проект
- **💡 Build opportunity:** Это может быть следующий Semaphore. Managed hosting / enterprise версия. Нужно разобраться с командой и планами.
- **→ Рекомендация: перевести в Research, найти мейнтейнеров**

---

## 📊 Все новые идеи за сутки (11)

| # | Название | Источник | Категория | Первичный сигнал | Тег |
|---|---------|---------|-----------|-----------------|-----|
| 1 | Luminous AI | HN + PH + TG | AI / Fintech | Show HN #1, 487 pts | 🔥invest |
| 2 | Infractl | GitHub + Reddit | DevOps / Infra | 8.7K stars, trending #3 | 💡build |
| 3 | PaySync | Product Hunt | Fintech | PH #8, 340 upvotes | invest |
| 4 | CodeLens | Hacker News | DevTools | Show HN, 156 pts | invest |
| 5 | AIтестер | Telegram: Product Radar | QA / AI | Описание, URL | invest |
| 6 | DataForge | Reddit r/SaaS | Data / B2B | "Just hit $8K MRR" post | invest |
| 7 | NeuralSearch | GitHub Trending | AI / Search | 620 stars за день | invest |
| 8 | Voicely | Betalist | Consumer / AI | Beta launch | invest |
| 9 | CloudPipe | HN Who's Hiring | Infra | Нанимают 12 инженеров | invest |
| 10 | GameForge SDK | Habr | GameDev | Статья с 45 upvotes | 💡build |
| 11 | РобоФинанс | vc.ru | Fintech / RU | Статья "привлёк 20 млн" | invest |

---

## 📈 Движение в pipeline

**Готовы к Research** (в Ideas >7 дней, рекомендуется двигать):
- SpectraDB (9 дней) — vector DB, 3 источника
- FlowChat (8 дней) — AI customer support, YC W25
- NanoML (7 дней) — edge ML framework, GitHub trending

**Свежие заключения из Analysis:**
| Стартап | Score | Verdict | Ключевая причина |
|---------|:-----:|---------|-----------------|
| MeshPay | 8.1 | ⚡ INVEST | Сильный финтех-фаундер + растущий MRR |
| CodeWeave | 7.0 | 👀 WATCH | Отличная команда, нужен fundraising status |
| BotFactory | 4.2 | ❌ PASS | Слабый продукт, нет traction |

---

## 💡 Build Opportunities (идеи для собственных продуктов)

### Горячая ниша: AI-powered QA / тестирование
- **Сигнал:** YC W25 — 4 стартапа в этой нише. GitHub — 3 trending repos за месяц. 
  Reddit — рост обсуждений на 200%.
- **Конкуренты:** Все маленькие, нет доминирующего игрока
- **iFree fit:** У Just AI есть интерпрайз-клиенты, которым нужно тестирование
- **Оценка:** BUILD score 7.5 — стоит проработать

### Open-source для коммерциализации: GameForge SDK
- **Сигнал:** 4,200 stars, 23 contributors, но нет компании / монетизации
- **Что можно сделать:** Managed platform + marketplace ассетов
- **iFree fit:** Геймдев в фокусе, есть компетенции
- **Оценка:** BUILD score 6.8 — мониторить

---

## 📉 Источники: эффективность за неделю

| Источник | Новых идей | Прошли в Research | Конверсия |
|----------|:---:|:---:|:---:|
| GitHub Trending | 18 | 5 | 28% |
| Hacker News | 12 | 4 | 33% |
| Product Hunt | 9 | 2 | 22% |
| Telegram каналы | 8 | 3 | 38% |
| Reddit | 7 | 1 | 14% |
| vc.ru | 4 | 1 | 25% |
| YC Companies | 3 | 3 | 100% |
| Прочие | 5 | 1 | 20% |
| **Итого** | **66** | **20** | **30%** |

---

*Сгенерировано автоматически. Следующий digest: завтра 08:00 UTC.*
*Чтобы отметить стартап: добавьте тег 🔥invest или 💡build в файл идеи.*
```

---

## 6.2. Weekly Report

**Когда:** каждый понедельник
**Для кого:** стратегический обзор для принятия решений
**Формат:** более длинный, аналитический документ

---

### Пример Weekly Report

```markdown
# 📋 Weekly Scouting Report — Неделя 16 (14–20 апреля 2025)

## Executive Summary

За неделю система обработала **66 новых идей** из 12 источников. 
**20 перешли в Research** (конверсия 30%). 
Завершено **6 полных анализов**. 

**Результаты анализа:**
- ⚡ INVEST: 2 стартапа (Luminous AI, MeshPay)
- 👀 WATCH: 2 стартапа (CodeWeave, FlowChat)
- ❌ PASS: 2 стартапа (BotFactory, QuickApp)

**Build opportunities:** 1 горячая ниша (AI QA), 1 open-source проект (GameForge SDK)

---

## ⚡ INVEST Candidates — полные карточки

### Luminous AI
| | |
|---|---|
| **Score** | 8.4 / 10 |
| **Что делает** | AI-агент для финансового анализа. Подключается к Bloomberg, Reuters, SEC filings. Автоматически генерирует investment memos, risk assessments, market comparisons. |
| **Фаундеры** | **Dmitry Volkov** — ex-Goldman Sachs VP (8 лет), CFA. Co-founded DataBridge (data analytics, acquired 2022 ~$5M). Technical background: MS CS MIT. **Anna Park** — ex-JPMorgan, quant researcher, PhD Math Columbia. |
| **Traction** | GitHub: 2,100 stars (5 дней). Waitlist: 4,000+. Show HN: #1 за день (487 pts, 230 comments). Product Hunt: #2 (1,240 upvotes). 3 упоминания в Telegram (Edinorog, Product Radar, Стартап дня). |
| **Стадия / Fundraising** | Pre-seed. На сайте "Backed by..." — пока пусто. В HN-комментариях фаундер написал "we're raising, DM me". Предположительно ищут $300K–$500K. |
| **Бизнес-модель** | Free tier для индивидуалов. Teams: $49/user/month. Enterprise: custom. |
| **Конкуренты** | AlphaSense ($2.3B valuation), Tegus, Visible Alpha. Но все — enterprise, тяжёлые. Luminous — лёгкий, AI-native, для small funds и analysts. |
| **Почему ЗА** | (1) Exceptional founders — Goldman + JPMorgan + prev exit. (2) Быстрый organic traction — тройное совпадение источников. (3) Наш тезис: AI + fintech. (4) Чек подходит. (5) iFree может дать B2B-контакты в финансовом секторе. |
| **Почему ПРОТИВ** | (1) Конкуренция с AlphaSense (но разные сегменты). (2) US-based — сложнее управлять. (3) Может быстро вырасти из нашего чека. |
| **Недостаточно информации** | Revenue (есть ли?), конкретный размер раунда, cap table, планы по geo expansion. |
| **Рекомендация** | ⚡ **INVEST — связаться в ближайшие 48 часов.** Warm intro через LinkedIn (2nd degree connection через [имя]). |
| **Следующие шаги** | 1. Найти warm intro. 2. Intro call. 3. Запросить deck. 4. Due diligence. |

### MeshPay
| | |
|---|---|
| **Score** | 8.1 / 10 |
| **Что делает** | Платёжная инфраструктура для B2B-маркетплейсов. Split payments, escrow, compliance — в одном API. |
| **Фаундеры** | **Igor Petrov** — ex-Stripe (Senior Eng, 4 года), ex-Yandex.Money. **Maria Sidorova** — ex-Revolut (Product Lead), ex-Сбер. |
| **Traction** | 12 клиентов (маркетплейсы). MRR: $8K (публичный пост на r/SaaS). Рост: 40% м/м последние 3 месяца. |
| **Стадия** | Seed. Ищут $200K–$400K. |
| **Fit с iFree** | Высокий. Just AI клиенты — часто B2B-платформы. Cross-sell потенциал. |
| **Рекомендация** | ⚡ **INVEST — идеальный fit по всем параметрам.** |

---

## 👀 WATCH List

| Стартап | Score | Почему watch | Когда пересмотреть |
|---------|:-----:|-------------|-------------------|
| CodeWeave | 7.0 | Сильная команда, нужен fundraising status | Через 2 нед — проверить рост |
| FlowChat | 7.2 | YC W25, но рано — только запустились | После Demo Day |

---

## 💡 Build Opportunities — детальный разбор

### Горячая ниша: AI-powered QA / автоматизация тестирования

**Почему эта ниша горячая:**
- YC W25: 4 стартапа (TestAI, QualityBot, BugHunter, AutoQA)
- GitHub: 3 trending repos за месяц в этой категории
- Reddit r/QualityAssurance: рост постов про AI-тестирование на 200% за квартал
- Product Hunt: 2 запуска за неделю

**Конкурентный ландшафт:**
- Все игроки маленькие (pre-seed/seed, <$1M revenue)
- Нет доминирующего игрока
- Большие (Selenium, Cypress) — не AI-native

**Что может сделать iFree:**
- AI-тестирование для enterprise (Just AI клиенты нуждаются в этом)
- Взять open-source базу (есть 3 варианта на GitHub с 1K+ stars)
- Managed service + white-label для интеграторов
- Целевая аудитория: текущие B2B-клиенты группы

**Build Score: 7.5 / 10**

| Критерий | Оценка | Комментарий |
|----------|:------:|-------------|
| Market opportunity | 8 | Горячая ниша, YC validates, нет лидера |
| iFree fit | 9 | Прямой cross-sell с клиентами Just AI |
| Technical feasibility | 7 | Есть open-source база, нужна кастомизация |
| Speed to market | 7 | MVP за 2-3 месяца |
| Revenue potential | 7 | B2B SaaS, $5K-50K/клиент/год |
| Defensibility | 5 | Средняя, data moat от клиентов |
| Trend alignment | 9 | Полное совпадение с AI + DevTools трендом |
| Gut feeling | 7 | Реалистично |

**Рекомендация: BUILD — начать с customer interviews с текущими клиентами iFree.**

---

## 📊 Тренды недели

### Растущие категории (по количеству сигналов)
1. **AI Code / DevTools** — 14 новых стартапов (+40% к прошлой неделе)
2. **AI Finance** — 8 новых стартапов (+60%)  
3. **Open-source Infrastructure** — 7 новых (+20%)
4. **AI Customer Support** — 5 новых (+25%)

### Falling off radar
- Crypto/Web3 — 1 стартап за неделю (было 5)
- No-code platforms — 2 стартапа (было 6)

### Интересные паттерны
- **"AI + legacy industry"** — 6 из 8 YC W25 компаний за эту неделю = AI-обёртка вокруг legacy workflow (финансы, HR, legal)
- **Open-source eating SaaS** — 3 open-source проекта с >5K stars предлагают бесплатную альтернативу дорогим SaaS ($50-200/mo → $0)

---

## 📋 Pipeline Status

```
1_ideas:     47 total | 11 new this week | 15 older than 7 days (→ move to research)
2_research:  12 total | 5 new this week  | 3 awaiting analysis
3_analysis:  8 total  | 6 new this week  | 2 INVEST | 2 WATCH | 2 PASS
_archive:    5 total  | 2 this week
```

---

*Сгенерировано: 21 апреля 2025, 08:00 UTC*
*Следующий weekly: 28 апреля*
```

---

## 6.3. Карточка стартапа (profile.md)

Подробный шаблон — в файле `TEMPLATE_profile.md`. Ключевые секции:
- Базовая информация (название, сайт, GitHub, страна, стадия, категория)
- Продукт (что делает, как работает, для кого)
- Traction (метрики, рост)
- Команда (фаундеры с бэкграундом)
- Финансирование
- Конкуренты
- Релевантность для iFree (invest + build)
- Открытые вопросы

## 6.4. Заключение (analysis.md)

Подробный шаблон — в файле `TEMPLATE_analysis.md`. Два варианта:
- **Invest Analysis:** скоринг по 10 критериям, за/против, рекомендация (INVEST/WATCH/PASS)
- **Build Analysis:** скоринг по 8 критериям, что можно построить, за/против, рекомендация (BUILD/PARTNER/MONITOR/SKIP)

## 6.5. Trend Report (ежемесячный)

```markdown
# 📈 Trend Report — Апрель 2025

## Топ-10 горячих ниш месяца (по количеству и качеству сигналов)

| # | Ниша | Новых стартапов | Avg Score | YC presence | Build opportunity? |
|---|------|:-:|:-:|:-:|:-:|
| 1 | AI Code Review | 23 | 6.8 | 5 in W25 | ⚠️ Конкурентно |
| 2 | AI Financial Analysis | 15 | 7.2 | 3 in W25 | ✅ Да |
| 3 | Open-source Observability | 12 | 6.5 | 2 in W25 | ✅ Да |
| 4 | AI QA / Testing | 11 | 6.9 | 4 in W25 | ✅ Да (hot) |
| 5 | AI Customer Support | 10 | 5.8 | 2 in W25 | ⚠️ Много конкурентов |
| 6 | AI for Legal | 9 | 7.0 | 3 in W25 | ✅ Да |
| 7 | Developer Infra | 8 | 6.2 | 1 in W25 | ⚠️ Capital-intensive |
| 8 | AI Content Creation | 8 | 5.1 | 0 in W25 | ❌ Commoditized |
| 9 | Edge ML | 6 | 7.1 | 1 in W25 | ✅ Да |
| 10 | Vertical SaaS + AI | 5 | 6.7 | 2 in W25 | ✅ Да |

## Open-Source Gems (проекты без компании, но с traction)

| Repo | Stars | Growth/mo | Что делает | Коммерческий потенциал |
|------|:-----:|:---------:|-----------|----------------------|
| infractl/infractl | 12,400 | +3,200 | Cloud infra management | Managed service, enterprise |
| gameforge/sdk | 4,200 | +1,100 | Game development SDK | Platform + marketplace |
| neurosearch/core | 3,800 | +900 | Neural search engine | Enterprise search SaaS |

## Founders to Watch (новая активность отслеживаемых людей)

| Имя | Что произошло | Релевантность |
|-----|-------------|--------------|
| Руслан Вахитов | Новый repo: AI-powered CRM | Знакомый, потенциальный invest |
| [ex-YC founder] | Registered new domain .ai | Tracking |

## Macro Signals

- **YC W25 Demo Day:** прошёл, 200 компаний, 40% — AI-first
- **GitHub Copilot competitors:** 7 новых за месяц, ниша перегрета
- **Российский рынок:** ФРИИ анонсировал новый батч, Сколково открыл AI-акселератор
```

## 6.6. Build Opportunities Report

Отдельный артефакт, фокус — на идеях для собственных продуктов.

```markdown
# 💡 Build Opportunities — Апрель 2025

## Рейтинг идей для собственных продуктов

### 🏆 #1. AI QA Platform (Build Score: 8.2)

**Ниша:** Автоматизированное тестирование с AI
**Почему сейчас:** 4 стартапа в YC W25, но все early. Нет доминирующего игрока.
**iFree advantage:** B2B-клиенты Just AI = готовый рынок для пилотов.
**Open-source база:** TestGenAI (2.1K stars), AutoTest (1.8K stars) — можно форкнуть.
**Что строить:** AI-тестирование для enterprise. Managed service.
**Ресурсы:** 1 сильный инженер + 1 продакт на 3 месяца.
**Revenue прогноз:** $5K–50K/клиент/год, breakeven при 10 клиентах.
**Следующий шаг:** Customer interviews с 5 текущими клиентами iFree — есть ли боль?

### 🥈 #2. Managed Infractl (Build Score: 7.5)

**Ниша:** Cloud infrastructure management  
**Почему сейчас:** Infractl набрал 12K stars, но нет hosted version.
**iFree advantage:** Опыт в инфраструктуре, можно white-label.
**Что строить:** Hosted infractl + enterprise features (RBAC, audit, SSO).
**Риск:** Команда Infractl может запустить hosted сами.
**Следующий шаг:** Связаться с мейнтейнерами, предложить партнёрство.

### 🥉 #3. AI Financial Assistant для российского рынка (Build Score: 7.1)

**Ниша:** То, что делает Luminous AI, но для российского рынка.
**Почему:** В России этого нет. Интеграция с MOEX, ЦБ, российскими банками.
**iFree advantage:** Знание российского рынка + финтех-компетенции.
**Риск:** Маленький рынок (Россия only).
**Следующий шаг:** Оценить TAM российского финтеха для such tool.
```

---

# Часть 7. 4-дневный план

Всё за 4 дня. Никаких фаз. Все парсеры с первого дня. К концу дня 4 — первый реальный дайджест.

## День 1: Фундамент + первые 5 парсеров

**Утро (2–3 часа):**
- Создать проект, структуру папок, шаблоны
- Написать `base_scout.py` (базовый класс)
- Написать `dedup.py` (дедупликация)

**День (4–5 часов):**
- `github_trending.py` — парсер GitHub trending
- `hackernews.py` — парсер Hacker News (Show HN)
- `producthunt.py` — парсер Product Hunt
- `reddit.py` — парсер Reddit (r/SaaS, r/startups, r/MachineLearning)
- `rss_feeds.py` — RSS парсер (TechCrunch, Crunchbase, vc.ru)

**Вечер:**
- Запустить все 5 парсеров, проверить что файлы появляются в 1_ideas/
- Починить баги

**Результат дня 1:** 5 работающих парсеров, 20–40 файлов в 1_ideas/

## День 2: Оставшиеся парсеры + Research скрипты

**Утро:**
- `telegram_channels.py` — парсер Telegram каналов (Telethon setup + 5 каналов)
- `vc_ru.py` — парсер vc.ru
- `habr.py` — парсер Habr

**День:**
- `yc_companies.py` — парсер YC Company Directory
- `indie_hackers.py` — парсер Indie Hackers
- `betalist.py` — парсер Betalist
- `founder_tracker.py` — мониторинг отслеживаемых фаундеров

**Вечер:**
- `enrich_github.py` — сбор GitHub-метрик
- `enrich_website.py` — сбор контента с сайтов
- `enrich_mentions.py` — поиск упоминаний
- `move_to_research.py` — скрипт переноса из Ideas в Research

**Результат дня 2:** 12–13 парсеров работают. Research-скрипты готовы. 50–80 файлов в 1_ideas/

## День 3: Анализ + Скоринг + Digest

**Утро:**
- `scoring.py` — модуль скоринга (invest mode + build mode)
- `analyze_startup.py` — агент-аналитик (Claude API, invest mode)
- `analyze_idea.py` — агент-аналитик (Claude API, build mode)

**День:**
- `daily_digest.py` — генератор ежедневного дайджеста
- `weekly_report.py` — генератор еженедельного отчёта
- `build_opportunities.py` — генератор отчёта по build-идеям
- `trends_report.py` — генератор отчёта по трендам

**Вечер:**
- Прогнать полный pipeline:
  - Все парсеры → 1_ideas/
  - Ручная выборка → move_to_research
  - Research enrichment
  - Analysis
  - Generate digest
- Проверить, что дайджест выглядит нормально

**Результат дня 3:** полный pipeline работает end-to-end. Первый реальный дайджест.

## День 4: Автоматизация + Polish + Launch

**Утро:**
- `run_all_scouts.sh` — единый скрипт запуска всех парсеров
- Cron setup: автопарсинг 3x/день, автодайджест утром
- `status.py` — показывает текущее состояние pipeline

**День:**
- Telegram-бот (опционально: /status, /new, /top, /digest)
- Или: настроить отправку дайджеста в email через Resend API
- Или: настроить отправку в Telegram-канал

**Вечер:**
- Тестирование полного цикла
- Доработка фильтров (слишком много шума? повысить пороги)
- Калибровка скоринга на первых 10 стартапах

**Результат дня 4:** система работает автономно. Дайджест приходит каждое утро.

## Что получаем после 4 дней

| Что | Статус |
|-----|--------|
| 13–15 парсеров из разных источников | ✅ Работают |
| Автоматический сбор 15–30 идей в день | ✅ В cron |
| Дедупликация | ✅ |
| Research enrichment (GitHub, website, mentions) | ✅ |
| AI-powered анализ (invest + build mode) | ✅ |
| Скоринг по 10/8 критериям | ✅ |
| Daily digest с горячими находками | ✅ |
| Build opportunities report | ✅ |
| Отправка в Telegram/email | ✅ |
| 50–100+ стартапов в pipeline | ✅ |

---

# Часть 8. Борьба с шумом

## Пороги входа (не попадают в Ideas)

| Источник | Отсечка |
|----------|---------|
| GitHub | Нет README >200 символов; tutorial/awesome-list; <50 stars/week; fork |
| HN | <50 points; не Show HN / Launch HN |
| Product Hunt | <100 upvotes; нет website |
| Reddit | <20 upvotes; нет URL; нет keyword match |
| Telegram | Нет URL; нет keyword match |
| RSS | Нет keyword match в title/description |

## Признаки «мамкиного стартапа» (auto-skip)

- Фаундер без LinkedIn/GitHub/публичного присутствия
- Нет работающего продукта (только landing page)
- Сайт на бесплатном хостинге без кастомного домена
- 0 contributors (solo без community)
- Только 1 упоминание за 30 дней
- Описание = generic "An awesome tool for..."

Если >3 признаков → не сохранять.

## Защита от накруток

GitHub stars spike без forks/issues/commits → пометить флагом, не повышать score.
Stars:forks >50:1 → подозрительно.
Нет упоминаний нигде кроме GitHub → скорее всего накрутка.

## Как не пропустить тихие проекты

- Founder-first tracking: мониторинг activity конкретных сильных людей
- YC lookalike search: похожие на YC-компании проекты, которые НЕ в YC
- «Паттерн Semaphore»: high stars + no Crunchbase + no media = hidden gem
- Low-signal / high-quality: 1–2 сигнала, но сильных (YC + strong founder)

---

# Часть 9. Промпты для Claude Code

20 конкретных задач. Каждая — один сеанс. Расположены в порядке 4-дневного плана.

## День 1

### Prompt 1: Проект и структура
```
Создай Python-проект scouting-pipeline.
Структура:
- 1_ideas/ 2_research/ 3_analysis/ _archive/ digests/ (пустые, с .gitkeep)
- scouts/ research/ analysis/ scripts/ config/
Файлы:
- README.md с описанием системы (скаутинг стартапов для инвестиций + поиск идей для собственных продуктов)
- THESIS.md (инвестиционный тезис: AI, fintech, gamedev, devtools; чек $30-300K; seed; сильные фаундеры)
- TEMPLATE_idea.md (шаблон: название, дата, источник, URL, GitHub, описание, почему интересно, страна, фаундер, категория, теги)
- TEMPLATE_profile.md (полный шаблон для research)
- TEMPLATE_analysis.md (шаблон с двумя секциями: invest analysis и build analysis)
- config/.env.example (GITHUB_TOKEN, ANTHROPIC_API_KEY, TELEGRAM_API_ID, TELEGRAM_API_HASH, RESEND_API_KEY)
- requirements.txt (httpx, beautifulsoup4, telethon, anthropic, markitdown, schedule, python-dotenv, Jinja2, feedparser)
```

### Prompt 2: Base Scout + Dedup
```
Создай scouts/base_scout.py — базовый класс BaseScout.
- fetch_url(url): HTTP GET с httpx, retry 3 попытки, timeout 15 сек, random user-agent
- save_idea(data: dict): создаёт MD-файл в 1_ideas/ по шаблону TEMPLATE_idea.md.
  Имя файла: {YYYY-MM-DD}_{slug}.md. Slug из name (lowercase, replace spaces with -, remove special chars).
  data: name, url, github_url, description, source, why_interesting, country, founder, category, tags
- already_exists(url, name): проверка дублей — grep по URL domain в 1_ideas/ + fuzzy name match (Jaro-Winkler >0.85)
- run(): abstract

Создай scouts/dedup.py:
- normalize_name(name): lowercase, remove Inc/Ltd/AI/Labs/.io/.ai/.dev/.com, strip
- extract_domain(url): urlparse → netloc, remove www.
- is_duplicate(url, name, directory="1_ideas"): exact domain match ИЛИ fuzzy name >0.85
- Используй простой Jaro-Winkler (напиши сам, не тяни библиотеку)
```

### Prompt 3: GitHub Trending
```
Создай scouts/github_trending.py наследуя BaseScout.
Парсит https://github.com/trending?since=daily и ?since=weekly.
Для каждого repo: name, full_name (org/repo), description, language, stars_today, total_stars, forks, url.
Фильтры — НЕ сохранять:
- Нет описания или < 20 символов
- Имя содержит: awesome-, tutorial, learning, interview, cheatsheet, roadmap
- stars_today < 50
- Это fork
Для прошедших → save_idea с source="GitHub Trending (daily)" или "(weekly)", category из language.
Запуск: python scouts/github_trending.py
```

### Prompt 4: Hacker News
```
Создай scouts/hackernews.py наследуя BaseScout.
API: https://hacker-news.firebaseio.com/v0/
1) Получи topstories (500 ids) и newstories (500 ids)
2) Для каждого item: загрузи /item/{id}.json
3) Фильтр: (title начинается с "Show HN" или "Launch HN") ИЛИ (score > 100 и url не ведёт на reddit/twitter/youtube)
4) Порог: score > 50
5) Для прошедших: title, url, score, by, descendants, time
6) name = title без "Show HN: " / "Launch HN: " prefix
7) save_idea с source="Hacker News (Show HN, {score} pts)"
Кеш: сохраняй обработанные item ids в config/.hn_seen (по одному id на строку), не обрабатывай повторно.
Лимит: обрабатывать не более 100 items за запуск.
```

### Prompt 5: Product Hunt + Reddit + RSS
```
Создай три парсера:

1) scouts/producthunt.py наследуя BaseScout.
   Парси https://www.producthunt.com/ через scraping (без API-ключа).
   Извлеки top-20 продуктов: name, tagline, website url, upvotes count.
   Фильтр: upvotes > 50.
   save_idea с source="Product Hunt (#{rank}, {upvotes} upvotes)"

2) scouts/reddit.py наследуя BaseScout.
   Парси JSON API: https://www.reddit.com/r/{sub}/hot.json?limit=50
   Subreddits: SaaS, startups, MachineLearning, selfhosted
   Фильтр: score > 20 + URL на внешний ресурс + keywords match
   Keywords: startup, launched, building, built, open source, show, MRR, revenue, users, side project, feedback
   Rate limit: 1 request per 2 sec. User-Agent required.
   save_idea с source="Reddit r/{sub} ({score} upvotes)"

3) scouts/rss_feeds.py наследуя BaseScout.
   Используй feedparser. Конфиг лент в config/sources.yaml (секция feeds: url, name, keywords).
   Для каждого feed: парси последние 20 entries.
   Фильтр: title или description содержит keywords из конфига.
   save_idea с source="{feed_name}"
```

## День 2

### Prompt 6: Telegram парсер
```
Создай scouts/telegram_channels.py.
Используй Telethon. Конфигурация каналов в config/telegram_channels.yaml.
Для каждого канала из конфига:
1) Получи последние 30 сообщений (или с last_checked из config/.telegram_state.json)
2) Фильтр: сообщение содержит URL + (keyword match ИЛИ keywords=[])
3) Извлеки все URL из текста (regex)
4) Для каждого URL: save_idea с name=первые 50 символов текста, source="Telegram: {channel_name}"
Обнови last_checked в state file.
Auth: при первом запуске — интерактивная авторизация Telethon (api_id, api_hash из .env).
```

### Prompt 7: vc.ru + Habr + Betalist + Indie Hackers
```
Создай четыре парсера, все наследуют BaseScout:

1) scouts/vc_ru.py — парси RSS https://vc.ru/rss/all
   Keywords: стартап, запуск, привлёк, раунд, инвестиц, seed, pre-seed, MVP, продукт, основатель, фаундер, open source
   save_idea с source="vc.ru"

2) scouts/habr.py — парси RSS https://habr.com/ru/rss/hub/startup/all/ и https://habr.com/ru/rss/hub/open_source/all/
   Фильтр: rating > 10 (если доступно в RSS).
   save_idea с source="Habr"

3) scouts/betalist.py — парси https://betalist.com/
   Scraping: список последних бета-запусков.
   save_idea с source="Betalist"

4) scouts/indie_hackers.py — парси https://www.indiehackers.com/
   Ищи посты с revenue milestones, launches.
   save_idea с source="Indie Hackers"
```

### Prompt 8: YC Companies + Founder Tracker
```
Создай два парсера:

1) scouts/yc_companies.py наследуя BaseScout.
   Парси https://www.ycombinator.com/companies (можно через API или scraping).
   Получи компании из последнего batch.
   Для каждой: name, description, url, batch, vertical, team_size, location.
   ВСЕ YC компании проходят фильтр (они уже pre-filtered).
   save_idea с source="Y Combinator ({batch})", tags=["#yc"]

2) scouts/founder_tracker.py наследуя BaseScout.
   Читай config/tracked_founders.yaml (list of: name, github, notes).
   Для каждого founder с github: через API проверь recent repos (created за 30 дней) и recent activity.
   Если есть новый repo → save_idea с source="Founder Tracker: {name}", tags=["#tracked_founder"]
```

### Prompt 9: Research скрипты
```
Создай 4 скрипта в research/:

1) research/enrich_github.py — принимает github_url, через API собирает:
   stars, forks, open_issues, watchers, contributors count, commits за 30д, languages, topics, created_at.
   Вычисляет: repo_age_days, stars_per_day, avg_commits_per_week.
   Сохраняет в {startup_dir}/github_metrics.md.

2) research/enrich_website.py — принимает website URL:
   Скачивает main page, /about, /pricing, /features, /team (если есть).
   Извлекает текст (beautifulsoup). Сохраняет в {startup_dir}/website_content.md.

3) research/enrich_mentions.py — принимает name и url:
   Ищет на HN (hn.algolia.com API) и Reddit (search JSON API).
   Сохраняет в {startup_dir}/social_mentions.md.

4) research/move_to_research.py — принимает путь к файлу в 1_ideas/:
   Создаёт папку в 2_research/{slug}/.
   Копирует исходный файл. Создаёт profile.md из шаблона.
   Запускает enrich_github, enrich_website, enrich_mentions.
   Usage: python research/move_to_research.py 1_ideas/2025-04-01_codeweave.md
   Также: python research/move_to_research.py --all-older-than 7 (все ideas старше 7 дней)
```

## День 3

### Prompt 10: Скоринг
```
Создай analysis/scoring.py.

Два скоринга:

1) invest_score(criteria: dict) -> dict:
   Веса: founder_strength=0.20, product=0.15, traction=0.15, market=0.10,
   business_model=0.10, technology=0.10, ifree_fit=0.10, momentum=0.05,
   fundraising_fit=0.03, gut_feeling=0.02
   Красные флаги: no_linkedin=-2, no_product=-2, fake_stars=-3
   Зелёные флаги: yc=+2, prev_exit=+2, warm_intro=+2, multi_source=+1
   Return: {total_score, breakdown, verdict: INVEST/WATCH/PASS}

2) build_score(criteria: dict) -> dict:
   Веса: market_opportunity=0.30, ifree_fit=0.25, technical_feasibility=0.15,
   speed_to_market=0.10, revenue_potential=0.10, defensibility=0.05,
   trend_alignment=0.03, gut_feeling=0.02
   Return: {total_score, breakdown, verdict: BUILD/PARTNER/MONITOR/SKIP}

Конфиг весов читать из config/scoring_weights.yaml (чтобы можно было менять без кода).
```

### Prompt 11: Агент-аналитик
```
Создай analysis/analyze_startup.py.

Принимает путь к папке в 2_research/{startup}/.
Читает ВСЕ .md файлы из папки, конкатенирует.
Отправляет в Claude API (anthropic SDK, model="claude-sonnet-4-20250514").

Промпт для invest mode:
"Ты инвестиционный аналитик. Данные о стартапе ниже. Инвестиционный тезис: {THESIS.md}.
Напиши анализ в формате: [скоринг по 10 критериям, 1-10 каждый] [аргументы ЗА 3-5] [аргументы ПРОТИВ 3-5] [недостаточно информации] [рекомендация: INVEST/WATCH/PASS] [следующие шаги].
Будь критичен. Не приукрашивай."

Промпт для build mode:
"Ты стратегический аналитик. Оцени этот стартап/проект как ИДЕЮ для собственного продукта iFree.
iFree — технологическая компания с B2B-клиентами. Вопрос: стоит ли нам самим построить подобный продукт?
Напиши: [скоринг по 8 критериям build mode] [что конкретно строить] [iFree advantages] [риски] [рекомендация: BUILD/PARTNER/MONITOR/SKIP] [следующий шаг]."

Сохраняет в 3_analysis/{startup}_analysis.md.
Usage: python analysis/analyze_startup.py 2_research/codeweave/ [--mode invest|build|both]
Default: --mode both (оба анализа в одном файле).
```

### Prompt 12: Daily Digest
```
Создай analysis/daily_digest.py.

Сканирует все папки и генерирует digest в Markdown.

Секции:
1. 🔥 Горячее (score ≥ 8 из 3_analysis/ за последние 7 дней)
2. 📊 Все новые идеи за 24ч (таблица из 1_ideas/ с сегодняшней датой)
3. 📈 Движение в pipeline (готовы к research, свежие заключения)
4. 💡 Build Opportunities (из analysis с build score ≥ 7)
5. 📉 Статистика источников (count по source из ideas за неделю)

Сохраняет в digests/{YYYY-MM-DD}_daily.md.

Опционально: отправка через Resend API (если RESEND_API_KEY задан) на email из .env.
Usage: python analysis/daily_digest.py [--send-email] [--send-telegram]
```

### Prompt 13: Weekly Report + Trends + Build Opportunities
```
Создай три генератора отчётов:

1) analysis/weekly_report.py — еженедельный отчёт.
   Executive summary, INVEST candidates (полные карточки), WATCH list, Build opportunities,
   тренды (растущие категории), pipeline status.
   Использует Claude API для генерации summary и trend analysis.
   Сохраняет в digests/{YYYY}-W{WW}_weekly.md.

2) analysis/trends_report.py — ежемесячный отчёт по трендам.
   Агрегирует все ideas за месяц по категориям. Считает: кол-во стартапов, avg score,
   YC presence, build opportunity. Топ-10 ниш. Open-source gems. Macro signals.
   Использует Claude API. Сохраняет в digests/{YYYY-MM}_trends.md.

3) analysis/build_opportunities.py — отчёт по идеям для собственных продуктов.
   Собирает все analysis с build mode, ранжирует по build_score.
   Для top-5: детальный разбор (ниша, iFree advantage, что строить, ресурсы, revenue прогноз).
   Сохраняет в digests/{YYYY-MM}_build_ideas.md.
```

## День 4

### Prompt 14: Run All + Cron + Status
```
Создай три утилитных скрипта:

1) scripts/run_all_scouts.sh — bash-скрипт, запускает все парсеры последовательно.
   Логирует время начала/конца каждого.
   При ошибке одного — продолжает остальные.

2) scripts/status.py — показывает текущее состояние:
   Ideas: X total (Y new today, Z older than 7 days)
   Research: X total
   Analysis: X total (N INVEST, M WATCH, K PASS)
   Archive: X total

3) scripts/full_pipeline.py — полный цикл:
   Запускает парсеры → показывает новые ideas → предлагает move to research (interactive) →
   enrichment → analysis → generate digest.

Также: инструкция для crontab в README:
0 8,16,0 * * * cd /path && bash scripts/run_all_scouts.sh
0 7 * * * cd /path && python analysis/daily_digest.py --send-email
0 7 * * 1 cd /path && python analysis/weekly_report.py
```

### Prompt 15: Telegram-бот / Email delivery
```
Создай output/telegram_bot.py (python-telegram-bot):
/status — состояние pipeline
/new — новые ideas за 24ч (список)
/top — top-5 по invest score
/build — top-3 build opportunities
/digest — последний дайджест (текст)

Автоалерты: при появлении analysis с invest score > 8 → сообщение в чат.

Config: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID в .env.

ИЛИ (если проще): создай output/send_email.py — отправка MD-файла через Resend API.
Usage: python output/send_email.py digests/2025-04-15_daily.md
```

### Prompt 16: YC Lookalike Search
```
Создай scouts/yc_lookalike.py.
1) Загрузи описания YC-компаний текущего батча (из 1_ideas/ с тегом #yc).
2) Для каждого описания: сформируй 2-3 поисковых запроса для GitHub Search API.
3) Найди repos, которые НЕ принадлежат YC-компании, но делают похожее.
4) Фильтр: >100 stars, коммиты за 30 дней, не fork.
5) save_idea с source="YC Lookalike (похож на {yc_company})", tags=["#yc_lookalike"]
```

### Prompt 17: Convert-to-MD утилита
```
Создай research/convert_to_md.py.
Конвертирует PDF, DOCX, XLSX, PPTX, HTML → Markdown через markitdown.
Usage:
  python research/convert_to_md.py path/to/file.pdf → создаёт file.md рядом
  python research/convert_to_md.py 2_research/startup/ → конвертирует все не-MD файлы в папке
```

### Prompt 18: Polish и документация
```
Обнови README.md:
- Quick Start (как установить и запустить за 5 минут)
- Описание каждого парсера
- Как добавить новый источник
- Как настроить cron
- Как работать с pipeline (invest mode vs build mode)
- FAQ и troubleshooting

Создай scripts/demo.py — демо полного цикла:
Создаёт фейковый стартап → Ideas → Research → Analysis → Digest.
```

---

# Часть 10. Ключевые принципы

1. **Все парсеры сразу, а не по фазам.** 15 парсеров за 2 дня. Широкий охват с первого дня — это принципиально. Лучше 15 простых парсеров, чем 3 идеальных.

2. **Два режима: Invest + Build.** Одни и те же данные, два разных анализа. Каждый стартап — и возможность инвестиции, и источник идеи для собственного продукта.

3. **4 дня, не 4 недели.** К вечеру дня 4 приходит первый реальный дайджест. Это не roadmap — это sprint.

4. **Дайджест — главный артефакт.** Система ценна не парсингом, а тем, что утром в Telegram/email приходит готовый обзор с рекомендациями.

5. **Три папки в git — вся архитектура.** Никаких БД, серверов, деплоев. Файловая система + скрипты + Claude API.

6. **Human-in-the-loop на переходах.** Автоматизация собирает и анализирует. Решения принимает человек. Особенно: перевод из Ideas в Research (осознанный выбор).

7. **Задержка — это фича.** Пауза между Ideas и Research фильтрует хайп. Через неделю виден настоящий сигнал.

8. **Каждый скрипт — независимый модуль.** Один файл = один парсер. Идеально для vibe coding: одна сессия Claude Code = один работающий скрипт.

9. **Фаундер > идея в invest mode. Рынок > технология в build mode.** Два разных фокуса, два скоринга.

10. **Warm intros — лучший канал.** Система дополняет, а не заменяет личные контакты. Стартап от знакомого → сразу в Ideas с бонусом.
