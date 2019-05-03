#!/usr/bin/python

import sys, getopt
import os
import json
import argparse
import re
import string

class StringBuilder:
  def __init__(self, type):
    self.type = type

  def build(self, string):
    return string

class SortedStringBuilder(StringBuilder):
  def build(self, string):
    return ''.join(sorted(string))

  @classmethod
  def fromJson(cls, data):
    return cls(**data)

class RemovePatternStringBuilder(StringBuilder):
  def __init__(self, type, patternString):
    StringBuilder.__init__(self, type)
    self.patternString = patternString
    print "Pattern string", patternString

  def build(self, string):
    p = re.compile(self.patternString, flags=re.UNICODE)
    result = p.sub('', string)
    return result

  @classmethod
  def fromJson(cls, data):
    return cls(**data)

class CompositeStringBuilder(StringBuilder):
  def __init__(self, type, stringBuilders):
    StringBuilder.__init__(self, type)
    self.stringBuilders = stringBuilders

  def build(self, string):
    resultString = string
    for builder in self.stringBuilders:
      resultString = builder.build(resultString)
    return resultString
  @classmethod
  def fromJson(cls, data):
    stringBuilders = list()
    for stringBuilderData in data["stringBuilders"]:
      stringBuilderType = eval(stringBuilderData["type"] + "StringBuilder")
      stringBuilders.append(stringBuilderType.fromJson(stringBuilderData))
    return cls("Composite", stringBuilders)

class UniqueCharacterContainer:
   def __init__(self):
      self.characters = set()

   def addCharactersFromText(self, text):
      self.characters.update([char for char in text])

   def getCharacters(self):
      return self.characters

   def getCharactersString(self, stringBuilder):
      return stringBuilder.build(''.join(self.characters))

class InputFile:
  def __init__(self, filepath, rules):
    self.filepath = filepath
    self.rules = rules

class InputConfig:
  def __init__(self, inputFiles):
    self.inputFiles = inputFiles

class OutputConfig:
  def __init__(self, outputFile, stringBuilder):
    self.outputFile = outputFile
    self.stringBuilder = stringBuilder

class ParseConfig:
  def __init__(self, inputConfig, outputConfig):
    self.inputConfig = inputConfig
    self.outputConfig = outputConfig

class JsonNodesExtractor:
  def __init__(self, jsonNode, rules, params):
    self.jsonNode = jsonNode
    self.rules = rules
    self.params = params

  @staticmethod
  def getJsonNodesViaRules(jsonNode, rules, params):
   if len(rules) == 0:
      return [jsonNode]
   currentRule = rules[0]
   results = list()
   if (currentRule == '[ANY]'):
      for k, v in jsonNode.items():
         results.extend(JsonNodesExtractor.getJsonNodesViaRules(v, rules[1:], params))

   m = re.search('\[ANY_OF\((.*)\)\]', currentRule)
   if (m is not None):
      items = m.group(1).split(', ')
      currentList = list()
      if (len(items) == 1 and items[0].startswith('"') == False):
        listName = m.group(1)
        currentList = params[listName]
      else:
        currentList = [item.strip('"').strip(' ') for item in items]
      for k, v in jsonNode.items():
        if (k in currentList):
         results.extend(JsonNodesExtractor.getJsonNodesViaRules(v, rules[1:], params))

   if (m == None):
     m = re.search('"(.*)"', currentRule)
     if (m != None):
        nodeName = m.group(1)
        if (isinstance(jsonNode, list)):
           for v in jsonNode:
              results.extend(JsonNodesExtractor.getJsonNodesViaRules(v[nodeName], rules[1:], params))
        else:
           results.extend(JsonNodesExtractor.getJsonNodesViaRules(jsonNode[nodeName], rules[1:], params))
   return results

  def extractNodes(self):
    return JsonNodesExtractor.getJsonNodesViaRules(self.jsonNode, self.rules, self.params)

def getTextFromLocFile(inputFile, rules, params):
  with open(inputFile) as jsonInput:
    data = json.load(jsonInput)
    nodesExtractor = JsonNodesExtractor(data, rules, params)
    outputString = ''.join(nodesExtractor.extractNodes())
    return outputString

def getRulesFromString(str):
  rules = str.split('.')
  return rules

def getParseConfigFromFile(configFile):
  with open(configFile) as config:
    jsonData = json.load(config)
    filesData = jsonData["input"]["files"]
    fileList = list()
    for fileData in filesData:
      rules = getRulesFromString(fileData["rules"])
      fileList.append(InputFile(fileData["file"], rules))

    inputConfig = InputConfig(fileList)
    outputData = jsonData["output"]
    outputFile = outputData["file"]
    outputRules = outputData["rules"]
    builderData = outputRules["builder"]
    builderType = eval(builderData["type"] + "StringBuilder")
    stringBuilder = builderType.fromJson(builderData)
    outputConfig = OutputConfig(outputFile, stringBuilder)
    return ParseConfig(inputConfig, outputConfig)

def writeTextToOutputFile(text, outputfile, encode):
  charactersFile = open(outputfile, "w")
  charactersFile.write(text.encode(encode))
  charactersFile.close()

def extractCharactersWithConfigFile(configFile):
  params = {}
  print "Extracting using config file"
  parseConfig = getParseConfigFromFile(configFile)
  uniqueCharacterContainer = UniqueCharacterContainer()
  print "Files amount ", len(parseConfig.inputConfig.inputFiles)
  for inputFile in parseConfig.inputConfig.inputFiles:
    if os.path.isfile(inputFile.filepath) == False:
      print 'Input File {0} does not exist. Please check correct path of Input File'.format(inputFile.filepath)
    else:
      print "file and rules:", inputFile.filepath, inputFile.rules
      text = getTextFromLocFile(inputFile.filepath, inputFile.rules, params)
      uniqueCharacterContainer.addCharactersFromText(text)
  outputString = uniqueCharacterContainer.getCharactersString(parseConfig.outputConfig.stringBuilder)
  print outputString
  writeTextToOutputFile(outputString, parseConfig.outputConfig.outputFile, "UTF-16")
  print "Characters extraction finished!"

def extractCharactersWithParams(inputfile, outputfile, langs, customRules):

  LOCALIZATION_RULE = "[ANY].[ANY_OF({0})]"
  LOCALIZATION_RULE_ALL_LANGS = "[ANY].[ANY]"
  DIALOGS_RULES = '"dialog"."dialogStep".[ANY]."text"'

  if os.path.isfile(inputfile) == False:
    print 'Input File {0} does not exist. Please check correct path of Input File'.format(inputfile)
    return

  params = {}
  rules = []
  if customRules != None:
    print "Using custom file rules"
    rules = customRules.split('.')
  elif inputfile.startswith("localization"):
    print "Using localization file rules"
    if (len(langs) == 1 and langs[0] == "all"):
      rules = LOCALIZATION_RULE_ALL_LANGS.split('.')
    else:
      rules = LOCALIZATION_RULE.format(', '.join(['"{0}"'.format(lang) for lang in langs])).split('.')
  elif inputfile.startswith("dialogs"):
    print "Using dialogs file rules"
    rules = DIALOGS_RULES.split('.')

  uniqueCharacterContainer = UniqueCharacterContainer()
  text = getTextFromLocFile(inputfile, rules, params)
  uniqueCharacterContainer.addCharactersFromText(text)
  outputString = uniqueCharacterContainer.getCharactersString(StringBuilder(""))
  print outputString
  writeTextToOutputFile(outputString, outputfile, "UTF-16")
  print "Characters extraction finished!"

def main():

   parser = argparse.ArgumentParser()
   parser.add_argument('--config_file', dest='config_file',
                    default=None,
                    help='Config file that contains information about input loc files, rules for parsing those files and output file')
   parser.add_argument('-i', action='store', dest='input_file',
                    help='Input file. Can be localization file or dialog file')
   parser.add_argument('-o', action='store', dest='output_file',
                    default='output.txt',
                    help='Output file. All found characters will be written in that file')
   parser.add_argument('--langs', dest='languages', nargs='*',
                    default=['all'],
                    help='List of languages that should be processed while extracting characters'
                    )
   parser.add_argument('--custom_rules', dest='custom_rules',
                    default=None,
                    help='If you use custom rules for extraction json node-leaves with text for your input file please specify them here. Example: "dialog"."dialogStep".[ANY]."text"'
                    )
   argResults = parser.parse_args()
   configFile = argResults.config_file
   inputfile = argResults.input_file
   outputfile = argResults.output_file
   langs = argResults.languages
   customRules = argResults.custom_rules

   if configFile != None:
    extractCharactersWithConfigFile(configFile)
   else:
    extractCharactersWithParams(inputfile, outputfile, langs, customRules)

if __name__ == "__main__":
   main()