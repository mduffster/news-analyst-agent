# About Parallax

In fast moving situations, it's difficult to get news without editorial slant problems. Social media democratizes info dissemination and gathering, but it is noisy, algorithmically filtered, and weird. Getting a clear picture of what's actually happening means reading widely and reconciling contradictions yourself. Most people don't have time for that.

AI is great for this. They synthesize and coalesce large amounts of information super fast. So that's what this project does.

## How it works

Each day, multiple AI models (currently Claude and GPT) independently research the same topic using web search. They receive a short topic prompt and minimal instruction. We keep the prompts lightweight on purpose, to encourage a wide range of research strategies. The less we constrain how each model approaches the topic, the more variety we get in what they find and what they emphasize. 

A synthesis model then reads the independent reports and produces a single unified briefing. It takes the best of what each model found and puts it into one readable report. 

The individual reports are always available if you want to see what each model produced on its own.

## Want me to add a topic?

You can contact me by using GitHub issues or by filling out the contact form. I'll fast track topics if you are willing to pay for the tokens, otherwise new additions are subject to my "editorial discretion". 

## Design principles

**Let models do what they do.** Minimal prompting means maximum information variety. We tell the models what to research, and what they did before, but we don't dictate sourcing or report structure.

**Label what you know and how well you know it.** Models tag claims by confidence: [VERIFIED] -- confirmed via multiple sources, [OFFICIAL] -- official public statements that could be used for misdirection, etc, [REPORTED] -- some reports exist, [UNCONFIRMED] -- rumors or hearsay. Not all information is equal, and the labels make that obvious.

**Quantify uncertainty.** Reports assign probability estimates to possible outcomes. This forces some quantification of what's actually likely, and makes it possible to track how assessments shift over time.

The whole pipeline runs automatically and publishes here. It works for any topic, and I am open to suggestions, though will exercise editorial discretion about topic choice. It takes about an hour to set up a new topic once approved. 

Built by [Matt Duffy](https://github.com/mduffster).
