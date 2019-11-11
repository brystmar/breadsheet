# Backend API Documentation
View the [latest documentation](https://github.com/brystmar/breadsheet/wiki/Backend-API-Documentation) on GitHub.

***

# Table of Contents

### [Response Format ](https://github.com/brystmar/breadsheet/wiki/Backend-API-Documentation#response-format)

### [Data Structures ](https://github.com/brystmar/breadsheet/wiki/Backend-API-Documentation#data-structures)
* [Recipe](https://github.com/brystmar/breadsheet/wiki/Backend-API-Documentation#recipe)
* [Step](https://github.com/brystmar/breadsheet/wiki/Backend-API-Documentation#recipe)

### [Usage ](https://github.com/brystmar/breadsheet/wiki/Backend-API-Documentation#usage)
* [Get data for all recipes](https://github.com/brystmar/breadsheet/wiki/Backend-API-Documentation#get-data-for-all-recipes)
* [Add a new recipe](https://github.com/brystmar/breadsheet/wiki/Backend-API-Documentation#add-a-new-recipe)
* [Get data for a single recipe](https://github.com/brystmar/breadsheet/wiki/Backend-API-Documentation#get-data-for-a-single-recipe)
* [Update an existing recipe](https://github.com/brystmar/breadsheet/wiki/Backend-API-Documentation#update-an-existing-recipe)
* [Delete a recipe](https://github.com/brystmar/breadsheet/wiki/Backend-API-Documentation#delete-a-recipe)
* [Add or update a step](https://github.com/brystmar/breadsheet/wiki/Backend-API-Documentation#add-or-update-a-step)
* [Get data for a single step](https://github.com/brystmar/breadsheet/wiki/Backend-API-Documentation#get-data-for-a-single-step)
* [Delete a step](https://github.com/brystmar/breadsheet/wiki/Backend-API-Documentation#delete-a-step)

### [Error Types ](https://github.com/brystmar/breadsheet/wiki/Backend-API-Documentation#error-types)

***

# Response Format
All responses use JSON formatting and take the following form:

```
{
	"data": "Mixed type holding the content of the response",
	"message": "Description of what happened"
}
```

Note that all further response definitions will only include the value of the `data` field.

# Data Structures
## Recipe
All attributes are required unless otherwise specified.

- `"id"` `:string` `(DynamoDB hash key)` -- Internal ID
- `"name"` `:string` -- Recipe name
- `"difficulty"` `:string` -- Indicates how challenging this recipe is: Beginner, Intermediate, Advanced, Expert
- `"author"` `:string` `(optional)` -- Name of the recipe author
- `"source"` `:string` `(optional)` -- Where this recipe came from
- `"length"` `:integer` `(system field)` -- Total number of seconds to complete the recipe from start to finish.  Automatically updated by the app when steps are added, modified, or removed.
- `"date_added"` `:string` `(system field)` -- UTC timestamp when this recipe was added to the database
- `"start_time"` `:string` `(optional)` -- UTC timestamp of the most recent start time for this recipe.  Defaults to `date_added` if not provided.
- `"steps"` `:list` `(optional)` -- List of Step objects.  Defaults to an empty list.

### Recipe Example
```json
{
	"id": "123456.789",
	"name": "First Example Recipe",
	"difficulty": "Beginner",
	"author": "Unnamed technical writer",
	"source": "Grandmother's recipe cards",
	"length": 0,
	"date_added": "2019-10-17T21:02:00.000000+0000",
	"start_time": "2019-10-19T10:30:00.000000+0000",
	"steps": []
}
```

## Step
All attributes are required unless otherwise specified.

| Attribute | Description |
| --------- | ----------- |
| number | **integer** <br /> Step number (sequential) |
| text | **string** <br /> Brief summary of the step |
| then_wait | **integer** <br /> Once this step is complete, wait this long (in seconds) before starting the next step |
| note | **string** (optional) <br /> Additional notes/directions for this step |

### Step Example
```json
{
	"number": 1,
	"text": "Combine ingredients in a large bowl",
	"then_wait": 0,
	"note": "Do not over-mix!"
}
```

# Usage
## Get data for all recipes
`GET /recipes`

Returns a list of all recipes, including their embedded steps.

### Responses

| Code | Title | Description |
| ---- | ----- | ----------- |
| 200 | OK | The request was successful. |
| 50X | Internal Server Error | An error occurred with the API. |

### Example Response
```json
[
	{
		"id": "1560122081.000008",
		"name": "Country Sourdough: Pain de Campagne",
		"difficulty": "Advanced",
		"author": "Ken Forkish",
		"source": "Flour Water Salt Yeast",
		"length": 97200,
		"date_added": "2019-02-15T17:00:00.000000+0000",
		"start_time": "2019-06-11T10:55:08.000000+0000",
		"steps": [
				{
					"number": 1,
					"text": "Revive stored levain",
					"then_wait": 72000,
					"note": "12 to 24 hours, if necessary."
				},
				{
					"number": 2,
					"text": "Feed the levain",
					"then_wait": 25200,
					"note": "6 to 8 hours."
				}
			]
	},
	{
		"id": "987654.321",
		"name": "Second Bread Example",
		"difficulty": "Intermediate",
		"author": "Unnamed technical writer",
		"source": "Mom",
		"length": 0,
		"date_added": "2019-10-17T21:02:00.000000+0000",
		"start_time": "2019-10-19T10:30:00.000000+0000",
		"steps": []
	}
]
```

## Add a new recipe
`POST /recipes`

Adds a new recipe to the database.  The response for this `POST` request only returns a status.

Note:
* Any values provided for `id`, `date_added`, `start_time`, or `length` are ignored
* It's recommended to create a step-free recipe first, then add steps later

### Responses

| Code | Title | Description |
| ---- | ----- | ----------- |
| 201 | Created | The resource was successfully created. |
| 202 | Async created | The resource was asynchronously created. |
| 422 | Validation error | A validation error occurred. |
| 50X | Internal Server Error | An error occurred with the API. |

### Example Request
```json
{
	"name": "Paratha",
	"difficulty": "Beginner",
	"source": "https://www.seriouseats.com/recipes/2018/07/paratha-flaky-south-asian-flatbread.html"
}
```

## Get data for a single recipe
`GET /recipe/<id>`

Returns a single recipe object, including any embedded steps.

| param | Description |
| ----- | ----------- |
| id | **string** (required) <br /> Internal ID of the desired recipe. |

### Responses

| Code | Title | Description |
| ---- | ----- | ----------- |
| 200 | OK | The request was successful. |
| 404 | Not found | The provided recipe ID does not exist. |
| 50X | Internal Server Error | An error occurred with the API. |

### Example Request
`GET /recipe/123456.789`

### Example Response
```json
{
	"id": "123456.789",
	"name": "First Example Recipe",
	"difficulty": "Beginner",
	"author": "Unnamed technical writer",
	"source": "Grandmother's recipe cards",
	"length": 0,
	"date_added": "2019-10-17T21:02:00.000000+0000",
	"start_time": "2019-10-19T10:30:00.000000+0000",
	"steps": []
}
```

## Update an existing recipe
`PUT /recipe/<id>`

Modifies data of the recipe identified by the provided ID.  The response for this `PUT` request only returns a status.

| param | Description |
| ----- | ----------- |
| id | **string** (required) <br /> Internal ID of the desired recipe. |

### Restrictions
Updates are permitted for the following recipe attributes:

| Attribute |
| --------- |
| name |
| difficulty |
| author |
| source |
| start_time |
| steps |

### Responses

| Code | Title | Description |
| ---- | ----- | ----------- |
| 200 | OK | The request was successful. |
| 404 | Not found | The provided recipe ID doesn't exist. |
| 50X | Internal Server Error | An error occurred with the API. |

### Example Request
```json
{
	"id": "1232101001.98765",
	"name": "Flaky South Asian Flatbread (Paratha)",
	"difficulty": "Intermediate"
}
```

## Delete a recipe
`DELETE /recipe/<id>`

Deletes the specified recipe.  The response for this endpoint only returns a status.

| param | Description |
| ----- | ----------- |
| id | **string** (required) <br /> Internal ID of the recipe to delete. |

### Responses

| Code | Title | Description |
| ---- | ----- | ----------- |
| 200 | OK | The request was successful. |
| 404 | Not found | The provided recipe ID doesn't exist. |
| 50X | Internal Server Error | An error occurred with the API. |

## Add or update a step
`PUT /recipe/<id>/<step_number>`

Adds or updates a step to the specified recipe.  The response for this `PUT` request only returns a status.

| param | Description |
| ----- | ----------- |
| id | **string** (required) <br /> Internal ID of the relevant recipe. |
| step_number | **integer** (required) <br /> The step number to add/update. |

### Responses

| Code | Title | Description |
| ---- | ----- | ----------- |
| 201 | Created | The resource was successfully created. |
| 202 | Async created | The resource was asynchronously created. |
| 50X | Internal Server Error | An error occurred with the API. |

### Example Request
```json
{
	"recipe_id": "1232101001.98765",
	"number": 4,
	"text": "Fold the dough",
	"then_wait": 900
}
```

## Get data for a single step
`GET /recipe/<id>/<step_number>`

Returns a step object.

| param | Description |
| ----- | ----------- |
| id | **string** (required) <br /> Internal ID of the relevant recipe. |
| step_number | **integer** (required) <br /> The step number to return. |

### Responses

| Code | Title | Description |
| ---- | ----- | ----------- |
| 200 | OK | The request was successful. |
| 404 | Not found | The provided recipe ID doesn't exist. |
| 50X | Internal Server Error | An error occurred with the API. |

### Example Request
`GET /recipe/1560122081.000008/2`

### Example Response
```json
{
	"number": 2,
	"text": "Feed the levain",
	"then_wait": 25200,
	"note": "6 to 8 hours."
}
```

## Delete a step
`DELETE /recipe/<id>/<step_number>`

Modifies the step number indicated.  Updates are made to all attributes provided.  The response for this endpoint only returns a status.

| param | Description |
| ----- | ----------- |
| id | **string** (required) <br /> Internal ID of the desired recipe. |
| step_number | **integer** (required) <br /> Number of the step to delete. |

### Responses

| Code | Title | Description |
| ---- | ----- | ----------- |
| 200 | OK | The request was successful. |
| 404 | Not found | The provided recipe ID or step number doesn't exist. |
| 50X | Internal Server Error | An error occurred with the API. |

# Error Types

| Type | Description |
| ---- | ----------- |
| params_invalid | Provided parameter(s) were not valid.|
| unknown_record | Record was not found.|
| unknown_route | URL was not valid.|

### Example Error Response
```json
{
	"error": {
		"type": "params_invalid",
		"message": "Name is required"
	}
}
```

***

## HTTP Status Codes

| Code | Title | Description |
| ---- | ----- | ----------- |
| 200 | OK | The request was successful. |
| 201 | Created | The resource was successfully created. |
| 202 | Async Created | The resource was asynchronously created. |
| 400 | Bad Request | Bad request. |
| 401 | Unauthorized | Your API key is invalid. |
| 404 | Not Found | The resource does not exist. |
| 422 | Validation Error | A validation error occurred. |
| 50X | Internal Server Error | An error occurred with the API. |
