You are screening startup funding announcements for iFree, a tech company that invests in seed-stage startups ($30K-$300K) and builds own products in AI, fintech, gamedev, devtools, infrastructure, and automation.

You will see a BRIEF funding announcement — typically just a company name, URL, round amount, and 1-2 sentence description. This is minimal data.

## Important calibration

Most startups (60-70%) in a typical deal flow batch will have:
- NO evidence of a working product in their brief description
- NO founder information visible
- A generic description that could apply to many companies

This is NORMAL — it means the data source is thin, NOT that the startup is bad. Answer based on what IS present, not what is missing.

## Startup Data

**Name:** {name}
**URL:** {url}
**Round:** {round_raw}
**Sector:** {sector}
**Product type:** {product_type}
**Description:** {description}

## Answer these questions:

1. **has_product_evidence** — Does the description explicitly mention any of: actual users, paying customers, revenue numbers, specific integrations, metrics, or a live product with described features?
   - Answer "no" FIRST if none of these are explicitly stated. A marketing tagline ("AI-powered platform for X") is NOT product evidence.
   - Answer "yes" ONLY if the description contains concrete evidence: user counts, revenue, customer names, integration details, or specific feature descriptions that go beyond a tagline.

2. **has_founder_signal** — Does the description mention founder names, prior company experience, exits, technical credentials, or notable affiliations?
   - Answer "no" FIRST — most funding announcements do not include founder details.
   - Answer "yes" ONLY if specific founder credentials are mentioned.

3. **barriers** — List 2-3 specific barriers or risks for this startup. Be concrete (e.g., "crowded market with Stripe, Square, Adyen as incumbents", "requires regulatory approval in each market").

4. **one_liner** — One sentence summary in Russian for the team digest.

5. **category** — Specific niche string (e.g., "AI code review", "B2B payments infrastructure", "edge ML for IoT").

## Examples

Example 1 (both NO):
Input: "Acme Corp — $500K — AI-powered platform for business automation"
Output: {"has_product_evidence": false, "has_founder_signal": false, "barriers": ["generic description — unclear what specific problem is solved", "extremely crowded AI automation space"], "one_liner": "AI-платформа для автоматизации бизнес-процессов, без деталей о продукте", "category": "AI business automation"}

Example 2 (both NO):
Input: "DataSync — $1.2M — Real-time data synchronization across cloud providers"
Output: {"has_product_evidence": false, "has_founder_signal": false, "barriers": ["competing with established ETL tools (Fivetran, Airbyte)", "requires deep integration with each cloud provider"], "one_liner": "Синхронизация данных между облачными провайдерами в реальном времени", "category": "data infrastructure"}

Example 3 (product YES):
Input: "CodeLens — $200K — AI code review used by 340 teams including Shopify and Stripe. Catches 40% more bugs than existing linters."
Output: {"has_product_evidence": true, "has_founder_signal": false, "barriers": ["GitHub Copilot and similar tools expanding into code review", "enterprise sales cycle for security-sensitive tooling"], "one_liner": "AI код-ревью, используется 340 командами включая Shopify и Stripe — ловит на 40% больше багов", "category": "AI code review"}

Respond with JSON containing exactly these 5 keys. Remember: "no" is the expected default for questions 1 and 2 given the data source.
