# JsonNodesExtractor

This is small example on Python of how one can get to some leaves of json nodes using simple rules(path) like:

```
"dialog"."dialogStep".[ANY]."text"
```

The main class for Json nodes extraction is `JsonNodesExtractor` which is responsible for giving you all nodes that are satisfies the rules. 

In this specific example I needed to parse some json files and get text from the node leaves then make set of unique characters of the text that is found.

Also it is example of using argparse python lib

Example usage of config file:
`python JsonNodesExtractor.py --config_file config.json`

*config.json*

```
{
	"input" : 
	{
		"files":
		[
			{
				"file" : "test1.json",
				"rules" : "\"dialog\".\"dialogStep\".[ANY].\"text\""
			},
			{
				"file" : "test2.json",
				"rules" : "[ANY].[ANY_OF(\"en\", \"zh-Hans\")]"
			}
		]
	},
	"output" :
	{
		"file" : "output.txt"
	}
}
```

Example usage of call arguments:
```
python JsonNodesExtractor.py -i localization.json -o output.txt --langs en it
```
