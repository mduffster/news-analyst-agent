# About Parallax

In fast moving situations, it's difficult to get news without editorial slant problems. Social media democratizes the info dissemination and gathering process, but it is noisy, algorithmically filtered, and shaped by whatever window you happen to be looking through. Getting a clear picture of what's actually happening on any given topic means reading widely and reconciling contradictions yourself. Most people don't have time for that.

But AI models are great at this. They read widely very quickly, and synthesize large amounts of information. That's what this project does.

## How it works

Each day, multiple AI models (currently Claude and GPT) independently research the same topic using web search. They receive a short topic brief — just scope and framing — and minimal instruction. We keep the scaffolding light on purpose. The less we constrain how each model approaches the topic, the more variety we get in what they find, how they frame it, and what they emphasize. 

A synthesis model then reads all the independent reports and produces a single unified briefing — the best of what each model found, reconciled into one readable report. 

The individual reports are always available if you want to see what each model produced on its own.

## Design principles

**Let models do what they do.** Minimal prompting means maximum information variety. We tell the models what to look at, not how to write about it.

**Label what you know and how well you know it.** Models tag claims by confidence: [VERIFIED], [OFFICIAL], [REPORTED], [UNCONFIRMED]. Not all information is equal, and the labels make that obvious.

**Quantify uncertainty.** Rather than vague hedging, reports assign probability estimates to possible outcomes. This forces clarity about what's actually likely, and makes it easy to track how assessments shift over time.

The whole pipeline runs automatically and publishes here as a static site. Topics can be anything — geopolitical conflicts, and I am open to suggestions. It takes about an hour to set up a new topic once approved. 

Built by [Matt Duffy](https://github.com/mduffster).
