---
colors: {model: gold}
slug: how-it-works
voice: ../../video/words/ch9.json
offset: 1.430
until: 58.280
---
## How it works

<!-- beat: pipeline stages="Your question;Language model;Plan from the semantic layer;SQL;Validator;DuckDB;Analysis;Language model writes the story" notes="in plain words|picks a plan, never a number|fixed metrics, fixed ways to split them||SELECT only, known tables and columns, your role's rows only|read-only, 5-second limit|mix versus rate, confidence intervals, data-quality checks|computed facts only" cols="white,gold,blue,blue,blue,teal,blue,gold" order="n0,1+n1,2+n2,*2,3+4+n4,5+n5,6+n6,7+n7,all" -->

Here is how it works.

Your question goes to a language $\text{model}$, but the $\text{model}$ never writes a number.

It picks a plan from a semantic layer: a fixed list of metrics, like success rate, and the ways you can split them.

So every definition stays the same, every time.

The plan becomes SQL, and a validator checks it before it runs: SELECT only, known tables and columns only, and only what your role may see.

DuckDB runs it read-only, with a 5-second time limit.

Then the analysis: the mix versus rate split, confidence intervals and the data-quality checks, on every answer.

Only then does the $\text{model}$ write the story, and it may use only the computed facts.

So, back to Monday morning: before noon, you know week 6 was a traffic shift, Coastal Bank was the real problem, and every number behind it can be checked.

That's the AI analyst.
