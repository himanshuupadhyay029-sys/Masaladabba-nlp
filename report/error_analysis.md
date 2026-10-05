# Error analysis (test set)

Total errors: **11**

## By error type

| Type | Count |
|---|---|
| boundary | 7 |
| wrong label | 3 |
| spurious | 1 |

## By label (gold label, or predicted label for spurious)

| Label | Count |
|---|---|
| INGREDIENT | 5 |
| PREP | 5 |
| UNIT | 1 |

## By cause (an error can have several)

| Cause | Count |
|---|---|
| unseen ingredient | 5 |
| other | 3 |
| prep after ingredient | 3 |
| Hinglish word | 1 |
| number inside prep | 1 |
| inside brackets | 1 |

## All errors

| Line | Type | Gold | Predicted | Causes |
|---|---|---|---|---|
| 2 tomatos finely chopped | wrong label | `tomatos` INGREDIENT | `tomatos` UNIT | unseen ingredient |
| 2 tsp coriander-cumin seeds (dhania-jeera) powder | boundary | `coriander-cumin seeds (dhania-jeera) powder` INGREDIENT | `dhania-jeera` INGREDIENT | unseen ingredient, Hinglish word |
| 20 cubes paneer | wrong label | `cubes` UNIT | `cubes` PREP | other |
| 1 cup Onions fried | wrong label | `fried` PREP | `fried` INGREDIENT | prep after ingredient |
| 6 - 8 Cashew nuts soaked in 2 tablespoons water | boundary | `soaked in 2 tablespoons water` PREP | `soaked in 2` PREP | prep after ingredient, number inside prep |
| 1 cup Kabuli Chana (White Chickpeas) washed and soaked overnight. | boundary | `washed and soaked overnight` PREP | `washed and soaked overnight.` PREP | prep after ingredient |
| 1 black cardamom | boundary | `black cardamom` INGREDIENT | `cardamom` INGREDIENT | unseen ingredient |
| 1/4 cup boiled green peas | boundary | `boiled` PREP | `boiled green peas` PREP | other |
| 1/4 cup boiled green peas | boundary | `green peas` INGREDIENT | `boiled green peas` PREP | unseen ingredient |
| ½ small sized capsicum (finely chopped (colour of your choice)) | boundary | `small sized` PREP | `small` PREP | other |
| ½ small sized capsicum (finely chopped (colour of your choice)) | spurious | — | `colour` INGREDIENT | unseen ingredient, inside brackets |
