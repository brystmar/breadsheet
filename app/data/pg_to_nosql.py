import json


def sort_list_of_dictionaries(unsorted_list, key_to_sort_by) -> list:
    return sorted(unsorted_list, key=lambda k: k[key_to_sort_by], reverse=False)


def diff(abbrev):
    if abbrev == "E":
        return "Easy"
    elif abbrev == "M":
        return "Medium"
    elif abbrev == "H":
        return "Hard"


def recipes_to_json(file_read='recipes.txt', file_write='breadsheet_data.py'):
    with open(file_read, "r") as r:
        recipes = r.readlines()
        recipes.sort()

        with open(file_write, "a") as w:
            w.write("recipes = [\n")
            i = 1
            for line in recipes:
                parsed = line[:-1].split('|')
                recipe = {
                    'id':           parsed[0],
                    'name':         parsed[1],
                    'author':       parsed[2],
                    'source':       parsed[3],
                    'difficulty':   diff(parsed[4]),
                    'date_added':   parsed[6][:10],
                    'start_time':   parsed[7][:19]
                    }

                w.write(json.dumps(recipe, indent=4))
                if i < len(recipes):
                    w.write(",\n\n")
                else:
                    w.write("\n]\n\n")
                i += 1


def steps_to_json(file_read='steps.txt', file_write='steps.py'):  # file_write='breadsheet_data.py'):
    with open(file_read, "r") as r:
        steps = r.readlines()
        steps.sort()

        recipe_id = 7
        with open(file_write, "a") as w:
            w.write(f"recipe{recipe_id}_steps = [\n")
            i = 1
            for line in steps:
                parsed = line[:-1].split('|')

                if recipe_id != int(parsed[1]):
                    i += 1
                    continue

                step = {
                    'number':       int(parsed[2]),
                    'text':         parsed[3],
                    'then_wait':    int(parsed[4]),
                    'note':      parsed[5]
                    }

                w.write(json.dumps(step, indent=4))
                if i < len(steps):
                    w.write(",\n\n")
                i += 1
            w.write("\n]\n\n")


def replacements_to_json(file_read='replacements.txt', file_write='breadsheet_data.py'):
    with open(file_read, "r") as r:
        replacements = r.readlines()
        with open(file_write, "a") as w:
            w.write("replacements = [\n")
            i = 1
            for line in replacements:
                parsed = line[:-1].split('|')
                rep = {
                    'old':      parsed[0],
                    'new':      parsed[1],
                    'scope':    parsed[2]
                    }

                w.write(json.dumps(rep, indent=4))
                if i < len(replacements):
                    w.write(",\n\n")
                else:
                    w.write("\n]\n\n")
                i += 1


# recipes_to_json()
steps_to_json()
# replacements_to_json()
