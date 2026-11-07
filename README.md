# Why Breadsheet?
Suppose you're invited to a picnic on Saturday afternoon. Captivated by your exemplary breadmaking skills over the years, the group asks you to bake a fresh loaf of sourdough.

Although you love sourdough, you're also aware it can be challenging to properly schedule. There are many time-sensitive steps in this process with a fair bit of downtime throughout.  You may need to start as early as Thursday(!) depending how your [levain](https://en.wikipedia.org/wiki/Sourdough#Starter) is stored. And if you don't already have a mature levain, you aren't making sourdough this week. 

But wait, this is `${DateJoke.getFullYear()}`!  There _must_ be a better way.

Enter [breadsheet](https://breadsheet.com): a scheduling tool for long bread recipes that calculates the start & finish times for the recipe itself.

Steps within a bread recipe often have a range of acceptable timing. Breadsheet shows you those ranges for the start (or finish) time specified, allowing you to play with those timings to fit that recipe into your schedule today. Focus on the bread, and leave the scheduling to breadsheet.

# App Structure
* **Backend:** Flask
* **Frontend:** React
* **Database:** Postgres (Neon)

Full documentation on the [wiki](https://github.com/brystmar/breadsheet/wiki/Backend-API-Documentation).
