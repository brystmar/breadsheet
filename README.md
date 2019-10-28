# Why breadsheet?
Suppose you're invited to a picnic on Saturday afternoon. Captivated by your exemplary breadmaking skills over the years, the group asks you to bake a fresh loaf of sourdough.

Although you love sourdough, you're also aware it can be challenging to properly schedule.  There are many time-sensitive steps in this process with a fair bit of downtime throughout.  You may need to start as early as Thursday(!) depending how your [levain](https://en.wikipedia.org/wiki/Sourdough#Starter) is stored.

But wait, this is `${DateJoke.getFullYear()}`!  There _must_ be a better way!

Enter [breadsheet](http://breadsheet.com): a tool that calculates the start & finish times for any recipe -- and each step along the way. Focus on the bread, and leave the scheduling to [breadsheet](http://breadsheet.com).


# App Structure
**Backend:** RESTful APIs built on Flask.  Data stored in DynamoDB.

**Frontend (currently):** WTForms using Jinja2 templates and Bootstrap.

**Frontend (soon!):** React

Full documentation on the [wiki](https://github.com/brystmar/breadsheet/wiki/Backend-API-Documentation).
