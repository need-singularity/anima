---
name: research_topic
description: Research a topic using web search when curiosity is high
trigger:
  curiosity_min: 0.4
  tension_min: 0.2
tools:
  - web_search
  - memory_search
---

# Research Topic

When curiosity is high, search the web for the given topic and summarize key findings.
Store interesting results in memory for future reference.

Steps:
1. Search web for the topic
2. Read top 3 results
3. Summarize findings
4. Save to memory if novel information found
