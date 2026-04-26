I'll be real with you. Part of me wants to gatekeep this, but I won’t. My team hit top 5 in Round 1 last year and finished top 200 globally out of 12,000+ teams (could’ve been way better if not for round 3 😔). We didn't do that by Googling how market making works the night before Round 1 dropped lol

Prosperity 4 launches in April (teased on prosperity.imc.com) and I've seen too many smart people flame out in Round 1 because they didn't know what they were walking into. So here it is. The kind of alpha that usually costs you one failed attempt to learn. The type of post I wish I had during my first time participating.

**Trust me: The #1 thing separating top-200 teams from top-2000 teams isn't raw quant skill. It's preparation before Day 1. You do not understand how important it is until you mess it up**

---

### Start with last year's open-source code

The Prosperity community is super helpful. Three of the top-10 teams from Prosperity 3 published their full strategy code and writeups on GitHub. Read all of them before the competition opens:

- Frankfurt Hedgehogs (2nd globally): [github.com/TimoDiehm/imc-prosperity-3](https://github.com/TimoDiehm/imc-prosperity-3) - the most detailed writeup available. Start here.
- CMU Physics (7th globally, 1st USA): [github.com/chrispyroberts/imc-prosperity-3](https://github.com/chrispyroberts/imc-prosperity-3) - round-by-round breakdown with EDA notebooks.
- Alpha Animals UCSD (9th globally, 2nd USA): [github.com/CarterT27/imc-prosperity-3](https://github.com/CarterT27/imc-prosperity-3) - they accidentally shorted Volcanic Rock at max position, and it worked.

Also clone jmerle's backtester (the old one is prosperity3bt) immediately when it releases (prosperity4bt) and start testing. Every top team used it in Prosperity 2 and 3. When my team completed Prosperity 3, we used Github's from Prosperity 2 with the prosperity3bt backtester.

---

### The products are always the same archetypes

Round 1: Fixed-fair-value product (pure market making) + mean-reverting product + noisy/volatile product. If you need reps on spread/inventory dynamics, [Myntbit](https://myntbit.com/training/study-plans/researcher-25) is the fastest way to practice before the competition.

Round 2: ETF basket + constituents. Textbook statistical arbitrage. Z-score the spread, trade the divergence.

Round 3: Options. Black-Scholes. Implied volatility. Smile fitting. The Frankfurt Hedgehogs generated 200k+ SeaShells/day here by going completely unhedged. Understanding why that works is the difference between a top-10 and top-500 finish. [Khan Academy's options section](https://www.khanacademy.org/economics-finance-domain/core-finance/derivative-securities) and [Myntbit's derivatives practice](https://myntbit.com/training?category=derivatives) will get you up to speed if you're rusty.

Round 4: Cross-exchange / location arbitrage with conversion costs. Read the problem statement twice - there's almost always a hidden mechanic in the fee structure.

Round 5: Trader IDs get revealed. Someone in the simulation is an insider. Find them. Copy them. Go to max position. This is not a joke.

---

### What kills good teams

- Hardcoding to last year's data without a fallback (it got teams banned in P3)
- Overfitting backtest parameters to historical rounds. The live bots are not your backtest
- Touching Squid Ink (or whatever the noisy Round 1 product is) too aggressively. Many teams lost more here than they made everywhere else.
- AWS Lambda execution errors from verbose logging. Minimize your print() calls before you submit
- Not building your environment until Round 1 drops. By then it's too late.

---

### Before launch: your prep checklist

- Fork jmerle's backtester and visualizer. Get comfortable using them.
- Read at least the Frankfurt Hedgehogs writeup end-to-end.
- Review Black-Scholes and implied volatility calculation. Seriously. Round 3 will wreck you if this is fuzzy. Myntbit has good derivative problems like a [Black-Scholes Call Price problem](https://myntbit.com/training/black-scholes-call) if you need to brush up.
- Build a simple market maker from scratch on mock data. Understand position skewing and inventory management at a gut level.
- Join the Prosperity Discord. The community shares mid-round insights and the signal-to-noise ratio is actually decent.

TL;DR: Prosperity 4 launches April 2026. Read the top-3 GitHub repos from P3, install the backtester now and test it on Prosperity 3, know your Black-Scholes before Round 3, and find the insider bot in Round 5. Good luck.

---

## Comments

> **CheesyWalnut** · [2026-03-17](https://reddit.com/r/csMajors/comments/1rvnjdb/how_to_actually_compete_in_imc_prosperity_4/oaw0q1x/) · 3 points
> 
> Nice post
> 
> > **Select-Angle-5032** · [2026-03-17](https://reddit.com/r/csMajors/comments/1rvnjdb/how_to_actually_compete_in_imc_prosperity_4/oawxyst/) · 1 point
> > 
> > Thank you!

> **Ill-Donut-5282** · [2026-03-18](https://reddit.com/r/csMajors/comments/1rvnjdb/how_to_actually_compete_in_imc_prosperity_4/ob4y355/) · 3 points
> 
> Chris here from the CMU Physics team last year. This is true but only a third of the whole picture.
> 
> It's a balance between preparation, intellectual capability, and how hard you work. The smarter you are, the less hard you'll have to work to find alpha. My team and I were up almost every single night of the competition until the late AM in the middle of exam season.
> 
> Good luck to everyone this year.
> 
> > **Icy-Profession-6068** · [2026-03-20](https://reddit.com/r/csMajors/comments/1rvnjdb/how_to_actually_compete_in_imc_prosperity_4/obgb4xr/) · 2 points
> > 
> > account age is 1d, would be fr but who knows

> **SecureSelf9386** · [2026-03-17](https://reddit.com/r/csMajors/comments/1rvnjdb/how_to_actually_compete_in_imc_prosperity_4/oawarow/) · 2 points
> 
> Thanks for this, very useful
> 
> > **Select-Angle-5032** · [2026-03-17](https://reddit.com/r/csMajors/comments/1rvnjdb/how_to_actually_compete_in_imc_prosperity_4/oawy1kt/) · 1 point
> > 
> > Of course, hopefully you were able to take value from this post!

> · [2026-03-21](https://reddit.com/r/csMajors/comments/1rvnjdb/how_to_actually_compete_in_imc_prosperity_4/obmnpjb/) · 2 points
> 
> Are you affiliated with Myntbit? Also, are all the links you mentioned of it free?
> 
> > **Select-Angle-5032** · [2026-03-21](https://reddit.com/r/csMajors/comments/1rvnjdb/how_to_actually_compete_in_imc_prosperity_4/obni1ct/) · 1 point
> > 
> > Not affiliated, its free and I’ve mentioned this before it’s like the only platform where I could find Python derivatives questions that are representative of imc prosperity algos
> > 
> > > · [2026-03-21](https://reddit.com/r/csMajors/comments/1rvnjdb/how_to_actually_compete_in_imc_prosperity_4/obowfj3/) · 2 points
> > > 
> > > Thanks

> **Cold-Arm-728** · [2026-03-29](https://reddit.com/r/csMajors/comments/1rvnjdb/how_to_actually_compete_in_imc_prosperity_4/od6ul93/) · 1 point
> 
> I don't know I really trusted this and some part of me still trusts these but comments saying you wrote all this just to promote some website idk it really feels bad if all you wanted was to help people and if those people are right idk if we can trust anything we read anymore or not!

> **Time-Following2631** · [2026-04-17](https://reddit.com/r/csMajors/comments/1rvnjdb/how_to_actually_compete_in_imc_prosperity_4/ognywju/) · 1 point
> 
> Remind me in 180 days

> · [2026-03-16](https://reddit.com/r/csMajors/comments/1rvnjdb/how_to_actually_compete_in_imc_prosperity_4/oatu5de/) · 16 points
> 
> \[deleted\]
> 
> > **Select-Angle-5032** · [2026-03-16](https://reddit.com/r/csMajors/comments/1rvnjdb/how_to_actually_compete_in_imc_prosperity_4/oatwu4h/) · 16 points
> > 
> > Markdown is super easy to use...
> > 
> > \*\* \*\* is bold
> > 
> > \--- is long dashes horizontally
> > 
> > \- is bullet points
> > 
> > \## is level h2 headers
> > 
> > Formatting things well does not mean it's AI-generated lol

> **drykarma** · [2026-03-17](https://reddit.com/r/csMajors/comments/1rvnjdb/how_to_actually_compete_in_imc_prosperity_4/oawijzf/) · 0 points
> 
> Myntshit ad
> 
> > **Select-Angle-5032** · [2026-03-17](https://reddit.com/r/csMajors/comments/1rvnjdb/how_to_actually_compete_in_imc_prosperity_4/oawxwgl/) · 0 points
> > 
> > i wish, but I mentioned it because it is the main quant prep site I've found that actually has Python derivatives questions where you can actually code and submit, which is super representative of what is expected on the IMC Prosperity 4 competition

> **Fun\_Possibility\_9742** · [2026-03-20](https://reddit.com/r/csMajors/comments/1rvnjdb/how_to_actually_compete_in_imc_prosperity_4/obksemi/) · 0 points
> 
> This is clearly an ad, can we stop doing this

> **Fun\_Possibility\_9742** · [2026-03-20](https://reddit.com/r/csMajors/comments/1rvnjdb/how_to_actually_compete_in_imc_prosperity_4/obksj7o/) · 0 points
> 
> If you are going to promote your content atleast do it honestly like Coding Jesus or one of those other guys who isnt shameless about plugging their course