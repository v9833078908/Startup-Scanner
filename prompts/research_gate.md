You are evaluating whether a startup has enough research evidence to warrant expensive deep analysis.

You have two data sources:
1. The startup's website content (scraped)
2. An LLM-synthesized research summary covering: founders, business model, competitors, traction, risks

## Startup Context

**Name:** {name}
**URL:** {url}
**Round:** {round_raw}
**Sector:** {sector}
**Description:** {description}

## Website Content (scraped)

{website_content}

## Research Summary

{research_notes}

## Evaluate on two tracks:

### Track A: Invest Evidence Check

Answer these 3 questions — did the research actually find useful data?

1. **has_team_data** — Did the research find specific information about founders or team? Names, backgrounds, prior companies, LinkedIn profiles, team size?
   - "yes": specific people or team details found
   - "no": generic or no team information

2. **has_traction_data** — Did the research find any traction evidence? Revenue, user counts, growth rates, notable customers, partnerships?
   - "yes": concrete numbers or named customers found
   - "no": no quantitative traction data

3. **has_competitive_context** — Did the research identify the competitive landscape? Named competitors, market positioning, differentiation?
   - "yes": specific competitors or market analysis found
   - "no": generic or no competitive data

### Track B: Build Opportunity Signals

Answer these 5 questions — is there a specific BUILD opportunity for iFree?

iFree context: tech company focused on AI, fintech, gamedev, devtools. Has B2B clients. Based in Russia, interested in CIS market opportunities.

1. **ru_gap_detected** — Based on the competitive landscape found in research, is there NO established company offering this product/service in Russia or CIS?
   - "yes": research shows competitors are US/EU only, no Russian players mentioned
   - "no": Russian competitors exist, OR cannot determine from available data
   DEFAULT: "no" — only answer "yes" with specific evidence of gap

2. **oss_commercializable** — Is this startup built on or is an open-source project with significant community but no clear monetization?
   - "yes": open-source mentioned, GitHub presence, community-driven, no clear revenue model
   - "no": commercial product, or no open-source component
   DEFAULT: "no"

3. **cross_sell_fit** — Could this product be useful to iFree's existing B2B tech clients (AI companies, fintech, gamedev studios)?
   - "yes": the product serves the same customer segment (B2B tech, developers, data teams)
   - "no": different customer segment
   DEFAULT: "no" — only "yes" if the fit is specific, not theoretical

4. **underserved_niche** — Based on competitive data, are there multiple small players but no dominant market leader?
   - "yes": research found fragmented market with no clear winner
   - "no": dominant player exists, OR market is too early/unclear
   DEFAULT: "no"

5. **clear_localization_path** — Could this product be adapted for CIS market in under 3 months?
   - "yes": software-only, no regulatory barriers, language is the main adaptation needed
   - "no": requires regulatory compliance, local partnerships, significant re-engineering
   DEFAULT: "no" — only "yes" if the path is genuinely simple

Respond with JSON containing exactly 8 keys (3 invest + 5 build). Default to "no" unless evidence supports "yes".
