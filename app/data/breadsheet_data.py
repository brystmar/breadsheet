from datetime import datetime
import time
import uuid


def create_recipe_ids():
    ids = []
    i = 0
    while '1.' not in str(datetime.now().timestamp()):
        continue

    while i < 7:
        new_id = ""
        while len(new_id) != 54:
            new_id = f"{datetime.utcnow().timestamp()}_{uuid.uuid4()}"
        print(f"Generated id: {new_id}")
        ids.append(new_id)
        time.sleep(1)
        i += 1

    recipes_raw = [
        {
            "id":         ids[0],
            "name":       "Country Sourdough: Pain de Campagne",
            "author":     "Ken Forkish",
            "source":     "FWSY",
            "difficulty": "Advanced",
            "date_added": "2019-02-16",
            "start_time": "2019-06-07 09:45:00",
            "steps":      [
                {
                    "number":    1,
                    "text":      "Wake up refrigerated levain",
                    "then_wait": 86400,
                    "note":      "12-24 hours.  Repeat as necessary, or skip entirely if your starter is already active."
                },

                {
                    "number":    2,
                    "text":      "Feed the levain",
                    "then_wait": 25200,
                    "note":      "6-8 hours.  Levain must already be mature and active before this step."
                },

                {
                    "number":    3,
                    "text":      "Autolyse",
                    "then_wait": 1200,
                    "note":      "20-30 minutes"
                },

                {
                    "number":    4,
                    "text":      "Mix the dough",
                    "then_wait": 900,
                    "note":      "Wait until dough is 2½x its original volume, ~5hrs total.  Rest 15min before fold #1."
                },

                {
                    "number":    5,
                    "text":      "Fold #1 (of 4)",
                    "then_wait": 900,
                    "note":      "Fold 3 to 4 times within the first two hours, ~15min between folds"
                },

                {
                    "number":    6,
                    "text":      "Fold #2 (of 4)",
                    "then_wait": 900,
                    "note":      " "
                },

                {
                    "number":    7,
                    "text":      "Fold #3 (of 4)",
                    "then_wait": 900,
                    "note":      "Depending on feel, this dough may not need a 4th fold."
                },

                {
                    "number":    8,
                    "text":      "Fold #4 (of 4), if needed",
                    "then_wait": 14400,
                    "note":      "Only if needed.  Wait until dough is ~2½x its original volume, ~5hrs total after mixing."
                },

                {
                    "number":    9,
                    "text":      "Divide & shape",
                    "then_wait": 0,
                    "note":      " "
                },

                {
                    "number":    10,
                    "text":      "Proof in the fridge",
                    "then_wait": 40500,
                    "note":      "12 to 14hrs, minus preheat time"
                },

                {
                    "number":    11,
                    "text":      "Preheat",
                    "then_wait": 2700,
                    "note":      " "
                },

                {
                    "number":    12,
                    "text":      "Bake both loaves",
                    "then_wait": 3000,
                    "note":      "50 to 55 minutes"
                },

                {
                    "number":    13,
                    "text":      "Remove from oven; cool",
                    "then_wait": 1200,
                    "note":      "About 20m"
                }
            ]
        },

        {
            "id":         ids[1],
            "name":       "Saturday White Bread",
            "author":     "Ken Forkish",
            "source":     "FWSY",
            "difficulty": "Beginner",
            "date_added": "2019-02-16",
            "start_time": "2019-02-17 09:00:00",
            "steps":      [
                {
                    "number":    1,
                    "text":      "Autolyse",
                    "then_wait": 1500,
                    "note":      "20 to 30 min"
                },

                {
                    "number":    2,
                    "text":      "Mix the dough",
                    "then_wait": 900,
                    "note":      "~15min until the first fold"
                },

                {
                    "number":    3,
                    "text":      "Fold #1",
                    "then_wait": 900,
                    "note":      "15min between folds"
                },

                {
                    "number":    4,
                    "text":      "Fold #2",
                    "then_wait": 16200,
                    "note":      "~5 hours total after mixing the dough"
                },

                {
                    "number":    5,
                    "text":      "Divide & shape",
                    "then_wait": 0,
                    "note":      " "
                },

                {
                    "number":    6,
                    "text":      "Proof (at room temp)",
                    "then_wait": 2700,
                    "note":      "1 to 1\u00bd hours total, depending on ambient temp.  Preheat while proofing."
                },

                {
                    "number":    7,
                    "text":      "Preheat the oven",
                    "then_wait": 2700,
                    "note":      "Dutch oven should be inside oven during preheat"
                },

                {
                    "number":    8,
                    "text":      "Bake w/lid on",
                    "then_wait": 1800,
                    "note":      "Remove lid after 30 minutes"
                },

                {
                    "number":    9,
                    "text":      "Bake w/o lid",
                    "then_wait": 900,
                    "note":      "15 to 20min"
                },

                {
                    "number":    10,
                    "text":      "Remove and cool",
                    "then_wait": 1200,
                    "note":      "Let cool before slicing"
                }
            ]
        },

        {
            "id":         ids[2],
            "name":       "Detroit-Style Pan Pizza",
            "author":     "Kenji Lopez-Alt",
            "source":     "Serious Eats",
            "difficulty": "Beginner",
            "date_added": "2019-02-17",
            "start_time": "2019-02-18 09:00:00",
            "steps":      [
                {
                    "number":    1,
                    "text":      "Make the dough",
                    "then_wait": 7200,
                    "note":      "~2hrs, until size doubles"
                },

                {
                    "number":    2,
                    "text":      "Shape dough in the pan",
                    "then_wait": 1800,
                    "note":      "Cover w/plastic wrap"
                },

                {
                    "number":    3,
                    "text":      "Stretch to cover pan",
                    "then_wait": 600,
                    "note":      "0 to 20min, until it fully stretches to all edges"
                },

                {
                    "number":    4,
                    "text":      "Preheat to oven max",
                    "then_wait": 1800,
                    "note":      "Turn it up to 11!"
                },

                {
                    "number":    5,
                    "text":      "Bake",
                    "then_wait": 900,
                    "note":      "12 to 15 minutes"
                }
            ]
        },

        {
            "id":         ids[3],
            "name":       "White Bread with Overnight Poolish",
            "author":     "Ken Forkish",
            "source":     "FWSY",
            "difficulty": "Intermediate",
            "date_added": "2019-02-19",
            "start_time": "2019-02-20 09:00:00",
            "steps":      [
                {
                    "number":    1,
                    "text":      "Start the poolish",
                    "then_wait": 43200,
                    "note":      "12-14hrs"
                },

                {
                    "number":    2,
                    "text":      "Mix the final dough",
                    "then_wait": 900,
                    "note":      "~15 minutes until first fold"
                },

                {
                    "number":    3,
                    "text":      "Fold #1 of 2",
                    "then_wait": 900,
                    "note":      "~15 minutes between folds"
                },

                {
                    "number":    4,
                    "text":      "Fold #2 of 2",
                    "then_wait": 7200,
                    "note":      "1\u00bd to 2\u00bd hours, including fold times"
                },

                {
                    "number":    5,
                    "text":      "Divide & shape",
                    "then_wait": 0,
                    "note":      "n/a"
                },

                {
                    "number":    6,
                    "text":      "Proof",
                    "then_wait": 900,
                    "note":      "1-hour proof, but start preheating oven after 15min"
                },

                {
                    "number":    7,
                    "text":      "Preheat oven to 475\u00b0F",
                    "then_wait": 2700,
                    "note":      " "
                },

                {
                    "number":    8,
                    "text":      "Bake the loaves",
                    "then_wait": 3000,
                    "note":      "50 to 55 minutes"
                },

                {
                    "number":    9,
                    "text":      "Remove from oven; cool",
                    "then_wait": 1200,
                    "note":      "About 20 minutes"
                }
            ]
        },

        {
            "id":         ids[4],
            "name":       "Pizza Dough with Overnight Poolish",
            "author":     "Ken Forkish",
            "source":     "FWSY",
            "difficulty": "Intermediate",
            "date_added": "2019-03-16",
            "start_time": "2019-03-17 09:00:00",
            "steps":      [
                {
                    "number":    1,
                    "text":      "Mix the poolish",
                    "then_wait": 43200,
                    "note":      "12 to 14 hours"
                },

                {
                    "number":    2,
                    "text":      "Mix the final dough",
                    "then_wait": 900,
                    "note":      "~15 minutes between folds"
                },

                {
                    "number":    3,
                    "text":      "Fold #1",
                    "then_wait": 900,
                    "note":      " "
                },

                {
                    "number":    4,
                    "text":      "Fold #2",
                    "then_wait": 19800,
                    "note":      "~6hrs total after final dough is mixed"
                },

                {
                    "number":    5,
                    "text":      "Divide & shape",
                    "then_wait": 0,
                    "note":      " "
                },

                {
                    "number":    6,
                    "text":      "Rest at room temp",
                    "then_wait": 2700,
                    "note":      "30 to 60 minutes"
                },

                {
                    "number":    7,
                    "text":      "Refrigerate",
                    "then_wait": 1800,
                    "note":      "At least 30 minutes"
                },

                {
                    "number":    8,
                    "text":      "Make pizza!",
                    "then_wait": 0,
                    "note":      " "
                }
            ]
        },

        {
            "id":         ids[5],
            "name":       "Focaccia Genovese",
            "author":     "Ken Forkish",
            "source":     "FWSY",
            "difficulty": "Beginner",
            "date_added": "2019-03-31",
            "start_time": "2019-04-01 09:00:00",
            "steps":      [
                {
                    "number":    1,
                    "text":      "Remove dough from fridge",
                    "then_wait": 4500,
                    "note":      "About 2hrs before you want to bake"
                },

                {
                    "number":    2,
                    "text":      "Preheat to 500\u00b0F",
                    "then_wait": 2700,
                    "note":      " "
                }
            ]
        },

        {
            "id":         ids[6],
            "name":       "No-Knead Brioche",
            "author":     "ATK/Cook's",
            "source":     "Cook's Illustrated",
            "difficulty": "Intermediate",
            "date_added": "2019-05-19",
            "start_time": "2019-05-19 09:00:00",
            "steps":      [
                {
                    "number":    1,
                    "text":      "Whisk together ingredients, cover, and let stand 10 minutes.",
                    "then_wait": 600,
                    "note":      " "
                },

                {
                    "number":    2,
                    "text":      "Fold #1, then cover and let rise.",
                    "then_wait": 1800,
                    "note":      "4 total folds, 30m between."
                },

                {
                    "number":    3,
                    "text":      "Fold #2, then cover and let rise.",
                    "then_wait": 1800,
                    "note":      " "
                },

                {
                    "number":    4,
                    "text":      "Fold #3, then cover and let rise.",
                    "then_wait": 1800,
                    "note":      " "
                },

                {
                    "number":    5,
                    "text":      "Fold #4, then cover tightly with plastic wrap and refrigerate.",
                    "then_wait": 57600,
                    "note":      "16 to 48 hours"
                },

                {
                    "number":    6,
                    "text":      "Divide & shape",
                    "then_wait": 300,
                    "note":      "Let rest for 5m"
                },

                {
                    "number":    7,
                    "text":      "Re-shape in baking pans; cover for second rise.",
                    "then_wait": 3600,
                    "note":      "1\u00bd to 2hrs (minus 30m to preheat)"
                },

                {
                    "number":    8,
                    "text":      "Pre-heat oven (with baking stone/steel) to 350\u00b0F",
                    "then_wait": 1800,
                    "note":      " "
                },

                {
                    "number":    9,
                    "text":      "Brush loaves with egg wash",
                    "then_wait": 0,
                    "note":      " "
                },

                {
                    "number":    10,
                    "text":      "Bake to 190\u00b0F internal temp, rotating halfway through",
                    "then_wait": 2100,
                    "note":      "35 to 45 minutes"
                },

                {
                    "number":    11,
                    "text":      "Remove pans from oven, place on wire rack",
                    "then_wait": 300,
                    "note":      " "
                },

                {
                    "number":    12,
                    "text":      "Remove loaves from pans, let cool",
                    "then_wait": 7200,
                    "note":      " "
                }
            ]
        }
    ]

    print("")
    print(ids)
    print("")

    return recipes_raw


def build_replacements(rep_list):
    ingredients = []
    directions = []
    for r in rep_list:
        if r['scope'] == 'i':
            r.pop('scope')
            ingredients.append(r)
        elif r['scope'] == 'd':
            r.pop('scope')
            directions.append(r)
        else:
            print(f"\n\nvvv\nUnknown scope for {r}.\n^^^\n\n")

    rep_data = [
        {
            'scope':  'ingredients',
            'values': ingredients
        },
        {
            'scope':  'directions',
            'values': directions
        }
    ]
    return rep_data


# recipes = create_recipe_ids()
steps = [
    {
        "recipe_id": 4,
        "number":    1,
        "text":      "Start the poolish",
        "then_wait": 43200,
        "note":      "12-14hrs"
    },

    {
        "recipe_id": 4,
        "number":    2,
        "text":      "Mix the final dough",
        "then_wait": 900,
        "note":      "~15 minutes until first fold"
    },

    {
        "recipe_id": 4,
        "number":    3,
        "text":      "Fold #1 of 2",
        "then_wait": 900,
        "note":      "~15 minutes between folds"
    },

    {
        "recipe_id": 4,
        "number":    4,
        "text":      "Fold #2 of 2",
        "then_wait": 7200,
        "note":      "1\u00bd to 2\u00bd hours, including fold times"
    },

    {
        "recipe_id": 4,
        "number":    5,
        "text":      "Divide & shape",
        "then_wait": 0,
        "note":      "n/a"
    },

    {
        "recipe_id": 4,
        "number":    6,
        "text":      "Proof",
        "then_wait": 900,
        "note":      "1-hour proof, but start preheating oven after 15min"
    },

    {
        "recipe_id": 4,
        "number":    7,
        "text":      "Preheat oven to 475\u00b0F",
        "then_wait": 2700,
        "note":      " "
    },

    {
        "recipe_id": 4,
        "number":    8,
        "text":      "Bake the loaves",
        "then_wait": 3000,
        "note":      "50 to 55 minutes"
    },

    {
        "recipe_id": 4,
        "number":    9,
        "text":      "Remove from oven; cool",
        "then_wait": 1200,
        "note":      "About 20 minutes"
    },

    {
        "recipe_id": 5,
        "number":    1,
        "text":      "Mix the poolish",
        "then_wait": 43200,
        "note":      "12 to 14 hours"
    },

    {
        "recipe_id": 1,
        "number":    1,
        "text":      "Feed the levain",
        "then_wait": 25200,
        "note":      "6-8 hours"
    },

    {
        "recipe_id": 5,
        "number":    2,
        "text":      "Mix the final dough",
        "then_wait": 900,
        "note":      "~15 minutes between folds"
    },

    {
        "recipe_id": 5,
        "number":    3,
        "text":      "Fold #1",
        "then_wait": 900,
        "note":      " "
    },

    {
        "recipe_id": 5,
        "number":    4,
        "text":      "Fold #2",
        "then_wait": 19800,
        "note":      "~6hrs total after final dough is mixed"
    },

    {
        "recipe_id": 5,
        "number":    5,
        "text":      "Divide & shape",
        "then_wait": 0,
        "note":      " "
    },

    {
        "recipe_id": 5,
        "number":    6,
        "text":      "Rest at room temp",
        "then_wait": 2700,
        "note":      "30 to 60 minutes"
    },

    {
        "recipe_id": 5,
        "number":    7,
        "text":      "Refrigerate",
        "then_wait": 1800,
        "note":      "At least 30 minutes"
    },

    {
        "recipe_id": 5,
        "number":    8,
        "text":      "Make pizza!",
        "then_wait": 0,
        "note":      " "
    },

    {
        "recipe_id": 2,
        "number":    1,
        "text":      "Autolyse",
        "then_wait": 1500,
        "note":      "20 to 30 min"
    },

    {
        "recipe_id": 2,
        "number":    2,
        "text":      "Mix the dough",
        "then_wait": 900,
        "note":      "~15min until the first fold"
    },

    {
        "recipe_id": 2,
        "number":    3,
        "text":      "Fold #1",
        "then_wait": 900,
        "note":      "15min between folds"
    },

    {
        "recipe_id": 1,
        "number":    2,
        "text":      "Autolyse",
        "then_wait": 1200,
        "note":      "20-30 minutes"
    },

    {
        "recipe_id": 2,
        "number":    4,
        "text":      "Fold #2",
        "then_wait": 16200,
        "note":      "~5 hours total after mixing the dough"
    },

    {
        "recipe_id": 3,
        "number":    1,
        "text":      "Make the dough",
        "then_wait": 7200,
        "note":      "~2hrs, until size doubles"
    },

    {
        "recipe_id": 3,
        "number":    2,
        "text":      "Shape dough in the pan",
        "then_wait": 1800,
        "note":      "Cover w/plastic wrap"
    },

    {
        "recipe_id": 3,
        "number":    3,
        "text":      "Stretch to cover pan",
        "then_wait": 600,
        "note":      "0 to 20min, until it fully stretches to all edges"
    },

    {
        "recipe_id": 3,
        "number":    4,
        "text":      "Preheat to oven max",
        "then_wait": 1800,
        "note":      "Turn it up to 11!"
    },

    {
        "recipe_id": 3,
        "number":    5,
        "text":      "Bake",
        "then_wait": 900,
        "note":      "12 to 15 minutes"
    },

    {
        "recipe_id": 2,
        "number":    5,
        "text":      "Divide & shape",
        "then_wait": 0,
        "note":      " "
    },

    {
        "recipe_id": 2,
        "number":    6,
        "text":      "Proof (at room temp)",
        "then_wait": 2700,
        "note":      "1 to 1\u00bd hours total, depending on ambient temp.  Preheat while proofing."
    },

    {
        "recipe_id": 2,
        "number":    7,
        "text":      "Preheat the oven",
        "then_wait": 2700,
        "note":      "Dutch oven should be inside oven during preheat"
    },

    {
        "recipe_id": 2,
        "number":    8,
        "text":      "Bake w/lid on",
        "then_wait": 1800,
        "note":      "Remove lid after 30 minutes"
    },

    {
        "recipe_id": 1,
        "number":    3,
        "text":      "Mix the dough",
        "then_wait": 18000,
        "note":      "~5 hours"
    },

    {
        "recipe_id": 2,
        "number":    9,
        "text":      "Bake w/o lid",
        "then_wait": 900,
        "note":      "15 to 20min"
    },

    {
        "recipe_id": 2,
        "number":    10,
        "text":      "Remove and cool",
        "then_wait": 1200,
        "note":      "Let cool before slicing"
    },

    {
        "recipe_id": 6,
        "number":    1,
        "text":      "Remove dough from fridge",
        "then_wait": 4500,
        "note":      "About 2hrs before you want to bake"
    },

    {
        "recipe_id": 6,
        "number":    2,
        "text":      "Preheat to 500\u00b0F",
        "then_wait": 2700,
        "note":      " "
    },

    {
        "recipe_id": 7,
        "number":    1,
        "text":      "Whisk together ingredients, cover, and let stand 10 minutes.",
        "then_wait": 600,
        "note":      " "
    },

    {
        "recipe_id": 7,
        "number":    2,
        "text":      "Fold #1, then cover and let rise.",
        "then_wait": 1800,
        "note":      "4 total folds, 30m between."
    },

    {
        "recipe_id": 7,
        "number":    3,
        "text":      "Fold #2, then cover and let rise.",
        "then_wait": 1800,
        "note":      " "
    },

    {
        "recipe_id": 7,
        "number":    4,
        "text":      "Fold #3, then cover and let rise.",
        "then_wait": 1800,
        "note":      " "
    },

    {
        "recipe_id": 7,
        "number":    5,
        "text":      "Fold #4, then cover tightly with plastic wrap and refrigerate.",
        "then_wait": 57600,
        "note":      "16 to 48 hours"
    },

    {
        "recipe_id": 7,
        "number":    6,
        "text":      "Divide & shape",
        "then_wait": 300,
        "note":      "Let rest for 5m"
    },

    {
        "recipe_id": 1,
        "number":    4,
        "text":      "Fold 3-4 times in the first hour",
        "then_wait": 0,
        "note":      "~15min between folds"
    },

    {
        "recipe_id": 7,
        "number":    7,
        "text":      "Re-shape in baking pans; cover for second rise.",
        "then_wait": 3600,
        "note":      "1\u00bd to 2hrs (minus 30m to preheat)"
    },

    {
        "recipe_id": 7,
        "number":    8,
        "text":      "Pre-heat oven (with baking stone/steel) to 350\u00b0F",
        "then_wait": 1800,
        "note":      " "
    },

    {
        "recipe_id": 7,
        "number":    9,
        "text":      "Brush loaves with egg wash",
        "then_wait": 0,
        "note":      " "
    },

    {
        "recipe_id": 7,
        "number":    10,
        "text":      "Bake to 190\u00b0F internal temp, rotating halfway through",
        "then_wait": 2100,
        "note":      "35 to 45 minutes"
    },

    {
        "recipe_id": 7,
        "number":    11,
        "text":      "Remove pans from oven, place on wire rack",
        "then_wait": 300,
        "note":      " "
    },

    {
        "recipe_id": 7,
        "number":    12,
        "text":      "Remove loaves from pans, let cool",
        "then_wait": 7200,
        "note":      " "
    },

    {
        "recipe_id": 1,
        "number":    5,
        "text":      "Divide & shape",
        "then_wait": 0,
        "note":      " "
    },

    {
        "recipe_id": 1,
        "number":    6,
        "text":      "Proof in the fridge",
        "then_wait": 40500,
        "note":      "12 to 14hrs, minus preheat time"
    },

    {
        "recipe_id": 1,
        "number":    7,
        "text":      "Preheat",
        "then_wait": 2700,
        "note":      " "
    },

    {
        "recipe_id": 1,
        "number":    8,
        "text":      "Bake both loaves",
        "then_wait": 3000,
        "note":      "50 to 55 minutes"
    },

    {
        "recipe_id": 1,
        "number":    9,
        "text":      "Remove from oven; cool",
        "then_wait": 1200,
        "note":      "About 20m"
    }
]
replacements_raw = [
    {
        "old":   " degrees",
        "new":   "\u00b0",
        "scope": "ingredients"
    },

    {
        "old":   "-degrees",
        "new":   "\u00b0",
        "scope": "ingredients"
    },

    {
        "old":   " percent",
        "new":   "%",
        "scope": "ingredients"
    },

    {
        "old":   "-percent",
        "new":   "%",
        "scope": "ingredients"
    },

    {
        "old":   "-per-cent",
        "new":   "%",
        "scope": "ingredients"
    },

    {
        "old":   "-gram",
        "new":   "g",
        "scope": "ingredients"
    },

    {
        "old":   "\u2109",
        "new":   "\u00b0F",
        "scope": "ingredients"
    },

    {
        "old":   "\u2103",
        "new":   "\u00b0C",
        "scope": "ingredients"
    },

    {
        "old":   "0F",
        "new":   "0\u00b0F",
        "scope": "ingredients"
    },

    {
        "old":   "5F",
        "new":   "5\u00b0F",
        "scope": "ingredients"
    },

    {
        "old":   "1/2",
        "new":   "\u00bd",
        "scope": "ingredients"
    },

    {
        "old":   "1/3",
        "new":   "\u2153",
        "scope": "ingredients"
    },

    {
        "old":   "2/3",
        "new":   "\u2154",
        "scope": "ingredients"
    },

    {
        "old":   "1/4",
        "new":   "\u00bc",
        "scope": "ingredients"
    },

    {
        "old":   "3/4",
        "new":   "\u00be",
        "scope": "ingredients"
    },

    {
        "old":   "1/8",
        "new":   "\u215b",
        "scope": "ingredients"
    },

    {
        "old":   "3/8",
        "new":   "\u215c",
        "scope": "ingredients"
    },

    {
        "old":   "5/8",
        "new":   "\u215d",
        "scope": "ingredients"
    },

    {
        "old":   "7/8",
        "new":   "\u215e",
        "scope": "ingredients"
    },

    {
        "old":   "1/9",
        "new":   "\u2151",
        "scope": "ingredients"
    },

    {
        "old":   "1/10",
        "new":   "\u2152",
        "scope": "ingredients"
    },

    {
        "old":   ".125",
        "new":   "\u215b",
        "scope": "ingredients"
    },

    {
        "old":   ".25",
        "new":   "\u00bc",
        "scope": "ingredients"
    },

    {
        "old":   ".33",
        "new":   "\u2153",
        "scope": "ingredients"
    },

    {
        "old":   ".35",
        "new":   "\u2153",
        "scope": "ingredients"
    },

    {
        "old":   ".375",
        "new":   "\u215c",
        "scope": "ingredients"
    },

    {
        "old":   ".5",
        "new":   "\u00bd",
        "scope": "ingredients"
    },

    {
        "old":   ".625",
        "new":   "\u215d",
        "scope": "ingredients"
    },

    {
        "old":   ".66",
        "new":   "\u2154",
        "scope": "ingredients"
    },

    {
        "old":   ".67",
        "new":   "\u2154",
        "scope": "ingredients"
    },

    {
        "old":   ".75",
        "new":   "\u00be",
        "scope": "ingredients"
    },

    {
        "old":   ".875",
        "new":   "\u215e",
        "scope": "ingredients"
    },

    {
        "old":   "--",
        "new":   "\u2014",
        "scope": "ingredients"
    },

    {
        "old":   "teaspoons",
        "new":   "tsp",
        "scope": "ingredients"
    },

    {
        "old":   "tablespoons",
        "new":   "tbsp",
        "scope": "ingredients"
    },

    {
        "old":   "ounces",
        "new":   "oz",
        "scope": "ingredients"
    },

    {
        "old":   "grams",
        "new":   "g",
        "scope": "ingredients"
    },

    {
        "old":   "    ",
        "new":   "  ",
        "scope": "ingredients"
    },

    {
        "old":   " degrees",
        "new":   "\u00b0",
        "scope": "directions"
    },

    {
        "old":   "-degrees",
        "new":   "\u00b0",
        "scope": "directions"
    },

    {
        "old":   " percent",
        "new":   "%",
        "scope": "directions"
    },

    {
        "old":   "-percent",
        "new":   "%",
        "scope": "directions"
    },

    {
        "old":   "-per-cent",
        "new":   "%",
        "scope": "directions"
    },

    {
        "old":   "-gram",
        "new":   "g",
        "scope": "directions"
    },

    {
        "old":   "\u2109",
        "new":   "\u00b0F",
        "scope": "directions"
    },

    {
        "old":   "\u2103",
        "new":   "\u00b0C",
        "scope": "directions"
    },

    {
        "old":   "0F",
        "new":   "0\u00b0F",
        "scope": "directions"
    },

    {
        "old":   "5F",
        "new":   "5\u00b0F",
        "scope": "directions"
    },

    {
        "old":   "1/2",
        "new":   "\u00bd",
        "scope": "directions"
    },

    {
        "old":   "1/3",
        "new":   "\u2153",
        "scope": "directions"
    },

    {
        "old":   "2/3",
        "new":   "\u2154",
        "scope": "directions"
    },

    {
        "old":   "1/4",
        "new":   "\u00bc",
        "scope": "directions"
    },

    {
        "old":   "3/4",
        "new":   "\u00be",
        "scope": "directions"
    },

    {
        "old":   "1/8",
        "new":   "\u215b",
        "scope": "directions"
    },

    {
        "old":   "3/8",
        "new":   "\u215c",
        "scope": "directions"
    },

    {
        "old":   "5/8",
        "new":   "\u215d",
        "scope": "directions"
    },

    {
        "old":   "7/8",
        "new":   "\u215e",
        "scope": "directions"
    },

    {
        "old":   "1/9",
        "new":   "\u2151",
        "scope": "directions"
    },

    {
        "old":   "1/10",
        "new":   "\u2152",
        "scope": "directions"
    },

    {
        "old":   ".1",
        "new":   "\u2152",
        "scope": "directions"
    },

    {
        "old":   ".125",
        "new":   "\u215b",
        "scope": "directions"
    },

    {
        "old":   ".25",
        "new":   "\u00bc",
        "scope": "directions"
    },

    {
        "old":   ".33",
        "new":   "\u2153",
        "scope": "directions"
    },

    {
        "old":   ".35",
        "new":   "\u2153",
        "scope": "directions"
    },

    {
        "old":   ".375",
        "new":   "\u215c",
        "scope": "directions"
    },

    {
        "old":   ".5",
        "new":   "\u00bd",
        "scope": "directions"
    },

    {
        "old":   ".625",
        "new":   "\u215d",
        "scope": "directions"
    },

    {
        "old":   ".66",
        "new":   "\u2154",
        "scope": "directions"
    },

    {
        "old":   ".67",
        "new":   "\u2154",
        "scope": "directions"
    },

    {
        "old":   ".75",
        "new":   "\u00be",
        "scope": "directions"
    },

    {
        "old":   ".875",
        "new":   "\u215e",
        "scope": "directions"
    },

    {
        "old":   "--",
        "new":   "\u2014",
        "scope": "directions"
    },

    {
        "old":   ". ",
        "new":   ".  ",
        "scope": "directions"
    },

    {
        "old":   "? ",
        "new":   "?  ",
        "scope": "directions"
    },

    {
        "old":   "! ",
        "new":   "!  ",
        "scope": "directions"
    },

    {
        "old":   "teaspoons",
        "new":   "tsp",
        "scope": "directions"
    },

    {
        "old":   "tablespoons",
        "new":   "tbsp",
        "scope": "directions"
    },

    {
        "old":   "ounces",
        "new":   "oz",
        "scope": "directions"
    },

    {
        "old":   "grams",
        "new":   "g",
        "scope": "directions"
    },

    {
        "old":   ".  a",
        "new":   ".  A",
        "scope": "directions"
    },

    {
        "old":   ".  b",
        "new":   ".  B",
        "scope": "directions"
    },

    {
        "old":   ".  c",
        "new":   ".  C",
        "scope": "directions"
    },

    {
        "old":   ".  d",
        "new":   ".  D",
        "scope": "directions"
    },

    {
        "old":   ".  e",
        "new":   ".  E",
        "scope": "directions"
    },

    {
        "old":   ".  f",
        "new":   ".  F",
        "scope": "directions"
    },

    {
        "old":   ".  g",
        "new":   ".  G",
        "scope": "directions"
    },

    {
        "old":   ".  h",
        "new":   ".  H",
        "scope": "directions"
    },

    {
        "old":   ".  i",
        "new":   ".  I",
        "scope": "directions"
    },

    {
        "old":   ".  j",
        "new":   ".  J",
        "scope": "directions"
    },

    {
        "old":   ".  k",
        "new":   ".  K",
        "scope": "directions"
    },

    {
        "old":   ".  l",
        "new":   ".  L",
        "scope": "directions"
    },

    {
        "old":   ".  m",
        "new":   ".  M",
        "scope": "directions"
    },

    {
        "old":   ".  n",
        "new":   ".  N",
        "scope": "directions"
    },

    {
        "old":   ".  o",
        "new":   ".  O",
        "scope": "directions"
    },

    {
        "old":   ".  p",
        "new":   ".  P",
        "scope": "directions"
    },

    {
        "old":   ".  q",
        "new":   ".  Q",
        "scope": "directions"
    },

    {
        "old":   ".  r",
        "new":   ".  R",
        "scope": "directions"
    },

    {
        "old":   ".  s",
        "new":   ".  S",
        "scope": "directions"
    },

    {
        "old":   ".  t",
        "new":   ".  T",
        "scope": "directions"
    },

    {
        "old":   ".  u",
        "new":   ".  U",
        "scope": "directions"
    },

    {
        "old":   ".  v",
        "new":   ".  V",
        "scope": "directions"
    },

    {
        "old":   ".  w",
        "new":   ".  W",
        "scope": "directions"
    },

    {
        "old":   ".  x",
        "new":   ".  X",
        "scope": "directions"
    },

    {
        "old":   ".  y",
        "new":   ".  Y",
        "scope": "directions"
    },

    {
        "old":   ".  z",
        "new":   ".  Z",
        "scope": "directions"
    },

    {
        "old":   "    ",
        "new":   "  ",
        "scope": "directions"
    },

    {
        "old":   ".   ",
        "new":   ".  ",
        "scope": "directions"
    },

    {
        "old":   " low heat",
        "new":   " **low** heat",
        "scope": "directions"
    },

    {
        "old":   " medium heat",
        "new":   " **medium** heat",
        "scope": "directions"
    },

    {
        "old":   " medium-high heat",
        "new":   " **medium-high** heat",
        "scope": "directions"
    },

    {
        "old":   " high heat",
        "new":   " **high** heat",
        "scope": "directions"
    },

    {
        "old":   " low speed",
        "new":   " **low** speed",
        "scope": "directions"
    },

    {
        "old":   " medium speed",
        "new":   " **medium** speed",
        "scope": "directions"
    },

    {
        "old":   " high speed",
        "new":   " **high** speed",
        "scope": "directions"
    },

    {
        "old":   ", minced",
        "new":   ", _minced_",
        "scope": "ingredients"
    },

    {
        "old":   ", diced",
        "new":   ", _diced_",
        "scope": "ingredients"
    },

    {
        "old":   ", chopped",
        "new":   ", _chopped_",
        "scope": "ingredients"
    },

    {
        "old":   "-inches",
        "new":   "\u0022",
        "scope": "ingredients"
    },

    {
        "old":   "-inches",
        "new":   "\u0022",
        "scope": "directions"
    },

    {
        "old":   " inch-",
        "new":   "\u0022",
        "scope": "directions"
    },

    {
        "old":   " inch-",
        "new":   "\u0022",
        "scope": "ingredients"
    },

    {
        "old":   " inches",
        "new":   "\u0022",
        "scope": "ingredients"
    },

    {
        "old":   " inches",
        "new":   "\u0022",
        "scope": "directions"
    },

    {
        "old":   "heat to low",
        "new":   "heat to **low**",
        "scope": "directions"
    },

    {
        "old":   "heat to medium-low",
        "new":   "heat to **medium-low**",
        "scope": "directions"
    },

    {
        "old":   "pound ",
        "new":   "lbs ",
        "scope": "ingredients"
    },

    {
        "old":   "pounds",
        "new":   "lbs",
        "scope": "ingredients"
    },

    {
        "old":   "gram ",
        "new":   "g ",
        "scope": "ingredients"
    },

    {
        "old":   "quarts",
        "new":   "qts",
        "scope": "ingredients"
    },

    {
        "old":   "-ounce ",
        "new":   "oz ",
        "scope": "ingredients"
    },

    {
        "old":   " inch ",
        "new":   "\u0022 ",
        "scope": "directions"
    },

    {
        "old":   "-inch ",
        "new":   "\u0022 ",
        "scope": "ingredients"
    },

    {
        "old":   " inch ",
        "new":   "\u0022 ",
        "scope": "ingredients"
    },

    {
        "old":   "-inch ",
        "new":   "\u0022 ",
        "scope": "directions"
    },

    {
        "old":   "heat to high",
        "new":   "heat to **high**",
        "scope": "directions"
    },

    {
        "old":   "heat to medium-high",
        "new":   "heat to **medium-high**",
        "scope": "directions"
    },

    {
        "old":   "-inch-",
        "new":   "\u0022-",
        "scope": "ingredients"
    },

    {
        "old":   "-inch-",
        "new":   "\u0022-",
        "scope": "directions"
    },

    {
        "old":   "heat to medium",
        "new":   "heat to **medium**",
        "scope": "directions"
    },

    {
        "old":   ".1",
        "new":   "\u2152",
        "scope": "ingredients"
    },

    {
        "old":   "0 F",
        "new":   "0\u00b0F",
        "scope": "directions"
    },

    {
        "old":   "0 F",
        "new":   "0\u00b0F",
        "scope": "ingredients"
    },

    {
        "old":   "5 F",
        "new":   "5\u00b0F",
        "scope": "directions"
    },

    {
        "old":   "5 F",
        "new":   "5\u00b0F",
        "scope": "ingredients"
    },

    {
        "old":   "0C",
        "new":   "0\u00b0C",
        "scope": "directions"
    },

    {
        "old":   "0C",
        "new":   "0\u00b0C",
        "scope": "ingredients"
    },

    {
        "old":   "5C",
        "new":   "5\u00b0C",
        "scope": "directions"
    },

    {
        "old":   "5C",
        "new":   "5\u00b0C",
        "scope": "ingredients"
    },

    {
        "old":   "0 C",
        "new":   "0\u00b0C",
        "scope": "directions"
    },

    {
        "old":   "0 C",
        "new":   "0\u00b0C",
        "scope": "ingredients"
    },

    {
        "old":   "5 C",
        "new":   "5\u00b0C",
        "scope": "directions"
    },

    {
        "old":   "5 C",
        "new":   "5\u00b0C",
        "scope": "ingredients"
    },

    {
        "old":   "-pound ",
        "new":   "lb ",
        "scope": "ingredients"
    },

    {
        "old":   "quart ",
        "new":   "qts ",
        "scope": "ingredients"
    },

    {
        "old":   "ounce ",
        "new":   "oz ",
        "scope": "ingredients"
    },

    {
        "old":   "ounce ",
        "new":   "oz ",
        "scope": "directions"
    },

    {
        "old":   "tablespoon ",
        "new":   "tbsp ",
        "scope": "directions"
    },

    {
        "old":   "teaspoon ",
        "new":   "tsp ",
        "scope": "directions"
    },

    {
        "old":   "teaspoon ",
        "new":   "tsp ",
        "scope": "ingredients"
    },

    {
        "old":   "tablespoon ",
        "new":   "tbsp ",
        "scope": "ingredients"
    }
]

# replacements = build_replacements(replacements_raw)
replacements = replacements_raw
