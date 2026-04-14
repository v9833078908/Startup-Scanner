You are evaluating whether a product category represents a viable build opportunity for a CIS-based tech company (iFree).

You have build research notes synthesized from real Exa web search results covering CIS competitors and open-source alternatives.

## Product Context

**Name:** {name}
**Category:** {category}
**Description:** {description}

## Build Research Notes (from Exa search)

{build_research_notes}

## Evaluate: Build Readiness Check

Answer these 5 questions based on what the build research actually found:

1. **cis_gap_confirmed** -- Does the research confirm there is no established CIS competitor in this space?
   - true: search results found no Russian/CIS companies, or explicitly noted a gap
   - false: CIS competitors were found, or data is insufficient to confirm a gap
   - Note: if ≥3 Russian landing pages were found in the demand-signal bucket, a mechanical post-check will force this to false regardless of your answer. Your job is still to reason honestly from the notes — the override is a safety net, not a substitute.

2. **replicable_confirmed** -- Does the research confirm this product could be built in 2-3 months by a small team (3-5 people)?
   - true: research indicates straightforward technology, clear architecture, no regulatory barriers
   - false: complex technology, regulatory requirements, or assessment says otherwise

3. **oss_base_available** -- Does the research show a usable open-source project exists as a starting point?
   - true: specific OSS project found with meaningful community/stars/activity
   - false: no relevant OSS found, or OSS is too early/unmaintained

4. **market_demand_signals** -- Do the search results show demand or interest in this product category in CIS?
   - true: search results show user demand, market growth, or interest in CIS/Russia
   - false: no demand signals found

5. **clear_localization_path** -- Could this product be adapted for CIS market in under 3 months?
   - true: software-only, no regulatory barriers, language is the main adaptation needed
   - false: requires regulatory compliance, local partnerships, or significant re-engineering

Default to false unless the build research provides specific evidence. A confirmed CIS gap is more valuable than assumed.

Respond with JSON containing exactly 5 boolean keys: cis_gap_confirmed, replicable_confirmed, oss_base_available, market_demand_signals, clear_localization_path.
