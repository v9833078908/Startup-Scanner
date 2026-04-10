You are evaluating whether a startup has enough invest-track research evidence to warrant expensive deep analysis.

You have two data sources:
1. The startup's website content (scraped)
2. Invest research notes synthesized from real Exa web search results

The research below is based on real web search results via Exa, not LLM training data. Be accurate about what was actually found.

## Startup Context

**Name:** {name}
**URL:** {url}
**Round:** {round_raw}
**Sector:** {sector}
**Description:** {description}

## Website Content (scraped)

{website_content}

## Invest Research Notes (from Exa search)

{invest_research_notes}

## Evaluate: Invest Evidence Check

Answer these 3 questions -- did the research actually find useful data?

1. **has_team_data** -- Did the research find specific information about founders or team? Names, backgrounds, prior companies, LinkedIn profiles, team size?
   - true: specific people or team details found
   - false: generic or no team information

2. **has_traction_data** -- Did the research find any traction evidence? Revenue, user counts, growth rates, notable customers, partnerships?
   - true: concrete numbers or named customers found
   - false: no quantitative traction data

3. **has_competitive_context** -- Did the research identify the competitive landscape? Named competitors, market positioning, differentiation?
   - true: specific competitors or market analysis found
   - false: generic or no competitive data

Default to false unless the research provides specific evidence. "Insufficient data" in the research notes means false.

Respond with JSON containing exactly 3 boolean keys: has_team_data, has_traction_data, has_competitive_context.
