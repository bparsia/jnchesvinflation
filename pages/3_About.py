import streamlit as st
from branding.branding import BLURB
from styles import inject_bjp_css, bjp

inject_bjp_css()

st.title("About")

bjp("""
# Who's writing this
Bijan Parsia (me) is the instigator of the app and any text styled like this is written by me.

Other text and the app itself has been developed using an AI coding tool, Claude CLI, using a personal account.

# What is this?

Primarily, this gathers and visualises the effect of inflation on the **JNCHES (Joint Negotiating Committee for Higher Education Staff)** national pay spine for UK Higher Education. Roughly, you can see the effects of inflation minus whatever increases we've managed to win. It's pretty brutal.

With this chart you can validate the UCU claim that our salaries have been eroded by 30%. Not *every* analysis will get you that and it won't be true for all spine points (the very low end gets upward pressure from the living wage...and is cheaper...and, properly, the unions try to weigh things to the lowest paid). However, it's pretty accurate for most UCU HE member spine points (and use RPI).

Probably the most commonly most helpful graph is the default: A good spread of spine points and starting from our salary peak, 2009. (If you do start of the data i.e., 2006, we actually had some real terms pay rises in there, but then it's all down hill.)

The dashed horizontal lines show, over time, what we'd need to be earning *now* (ok in 2024) to have no loss in purchasing power. Going down means losing purchasing power. It's grim! 

# Why is this?
UCU Commons member Michael Bartlett saw another Streamlit project I have built and said he wanted " a tool where staff can put their spinal point and start date in and see how much pay theyve lost to inflation since they joined". I, being excessive, did this even after pointing Michael to the [UCU pay modeller](https://www.ucu.org.uk/HEpaymodeller).

I don't think the UCU pay modeller is super helpful. It's terrible and it does seem to get the same results (assuming similar inputs), but:

1. You don't see *anything* until you've entered some numbers. That inhibits use.
2. It is tedious to compare things. I love me a good default but I do think being able to delve is critical. So being able to test CPI vs. RPI, starting points, and see multiple spine points makes a big difference. Also, you can guesstimate where you are just from my initial graph with default values. That's good for sharing.
3. The didn't release the data. It was annoying to extract the spine point data even with Claude assisting. It's in PDFs because UCEA sucks. I think this is useful data to have for other projects including by other people!

I care a lot about the presentation of information so this was fun.

# Who did this?
Er...Bijan Parsia, Professor of Computer Science at the University of Manchester, 2025-2026 NEC Representative for Disabled Members (HE), and UCU Commons member.

# Use of AI declaration
The data extraction scripts, Streamlit scripts, and some text was done by Claude CLI, an AI coding tool, under my direction. The code is all on Github. As the code itself is written by a tool, I do not believe that it is copyrightable in most jurisdictions, so no one owns it.

Whether it is at all possible to use any or any existing LLM based system ethically is an interesting question. As a Professor of Computer Science I have an obligation to my students especially in Software Engineering to teach them about these tools, the effect on methodology etc. and I cannot do that (at least, not well) without have experiential knowledge. This project would have taken an infeasibly long time for me to do by hand, given my current schedule. (And I would have 100% manually extracted the data. Tedious, but I was driven batty by the inconsistent PDFs when Claude was writing scripts!!!) The resulting code does not use an LLM so one could build on it and let me be your sin-eater.

So, from the point of view of totally clean hands, I don't have them. But I personally think while not ideal, it is ok enough for me to do it.

# Project status and roadmap

The Spine Points vs. Inflation are pretty well baked (though comments and corrections welcome). I would like to tease out first vs. final offers and some estimates around associated action. First vs. final gives us a (loose) idea of the marginal benefit of UCU/JNCHES negotiation. (I mean the lines just go down so the high level assessment is that we aren't making a large difference...but maybe! Gotta look to *know*.) One challenge is estimating the cost of action (to UCU, to members directly, to institutions). Honestly, that's a bit of a research project and I'd welcome expert collaboration.

The USS Scenarios is no where near done. It really is a very initial attempt to explore visualisations around conditional indexation but that quickly gets into first order modelling issues. And *that* gets into issues around investment strategies, valuations and valuation approaches, contributions...once you want to do rather realistic simulation of possibilities, you have to figure out a fair bit of that stuff if only to be able to attribute effects.

For example, my semi-historical scenario (i.e., using actual and interpolated historical funding ratios), all the CI approaches are dominated by the soft cap. But 1) we didn't have the soft cap over that history, 2) we had an extremely goofy valuation methodology, and 3) we had a goofy investment strategy tied ot the goofy valuation methodology. We know we won't have the goofy valuation methodology going forward so it's not helpful to tie us determinatively to the historical goofy numbers when trying to *project* the effects of CI.

Pensions have a lot of moving parts and they interact a lot.

I would like to have a fairly complete model of pensions (including TPS) and, ultimately, of total compensation (pay + pensions over lifetimes). But again, a ton of work and definitely a research paper out of it. Collaborators, welcome!

# UCU Commons projects
This is one of a series of projects we're working on at UCU Commons. Currently the are mostly "make data intelligible" and "model future improvements to the UCU website" style.

Good understanding is essential to good decision making. Democratising good understanding means doing the work to make both underlying information and analsyes built on that intelligible.

Another current project nearing maturing is the [UCU Election Data](https://ucuelectionsdata.streamlit.app/) app which tries to make all historical UCU national election data accessible and intelligible.

""")
