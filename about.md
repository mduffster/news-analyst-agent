# About Parallax

Parallax is for people who need to understand live issues quickly.

In fast-moving situations, it is hard to synthesize information while sorting through editorial slant, social media noise, and our own predilections. The best way to understand what is actually happening is to read widely and reconcile contradictions and ambiguities yourself. Busy people cannot do that every day.

That is why I built Parallax.

## How it works

Each day, multiple AI models independently research the same topic. A synthesis agent then combines what those models found into a single report.

I keep the prompts light on purpose. The less I constrain how each model approaches a topic, the more variety I get in what they find and what they emphasize.

The synthesis agent takes those separate reports and surfaces both disagreement and concurrence, while building an overall picture of the situation.

The individual reports are always available if you want to see what each model produced on its own.

## Want me to add a topic?

You can contact me through GitHub issues or by filling out the contact form. If you are willing to pay for the tokens, I will fast-track a topic. Otherwise, new additions are subject to my editorial discretion.

## Design principles

**Let models do what they do.** Minimal prompting means maximum information variety. I tell the models what to research, but I do not dictate sourcing or report structure.

**Label what you know and how well you know it.** Models tag claims by confidence: [VERIFIED] for claims confirmed across multiple sources, [OFFICIAL] for public statements that may still be misleading, [REPORTED] for claims that appear in reporting but are not fully nailed down, and [UNCONFIRMED] for rumors or hearsay. Not all information is equal, and the labels make that obvious.

**Quantify uncertainty.** Reports assign probability estimates to possible outcomes. That forces some quantification of what is actually likely and makes it possible to track how assessments shift over time.

The whole pipeline runs automatically and publishes here. It can work for any topic, and I am open to suggestions, though I will exercise editorial discretion in what I add. Once approved, a new topic usually takes about an hour to set up.

Built by [Matt Duffy](https://github.com/mduffster).