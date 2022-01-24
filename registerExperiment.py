import os
import git
import subprocess
import yaml
import hashlib
import collections
import warnings

EXPERIMENT_RESUME = "experimentResume.yaml"

path = "./"

repository = None

inputFolder = None
inputFiles = []

paramsFolder = None

commandsFile = "commands.txt"

experimentName = None

outputFolder = None
outputFiles = []

currentTag = None
tags = None


def isGitRepo(path) -> bool:
    try:
        git.Repo(path)
        return True
    except git.exc.InvalidGitRepositoryError:
        return False

def checkForChanges() -> None:
    changesNotAdded = [ item.a_path for item in repository.index.diff(None) ]
    changesAdded = [ item.a_path for item in repository.index.diff(repository.head.name) ]
    untrackedFiles = repository.untracked_files

    if ((len(changesNotAdded) + len(changesAdded) + len(untrackedFiles)) > 0):
        raise Exception("There are changes in the repository since the last commit, you can only register an experiment from a clean repository.")

def init(pathInput) -> None :
    global repository,path,experimentName,tags, currentTag
    if isGitRepo(pathInput):
        path += pathInput
        if not (pathInput[len(pathInput)-1] == "/"):
            path+="/"
        repository = git.Repo(path)
        experimentName = repository.active_branch.name
        os.chdir(path)
    else :
        raise Exception(f"{pathInput} is not a git repository")
    checkForChanges()
    tags = repository.tags
    currentTag = repository.git.describe('--tags')
    if not(currentVersionIsTagged()):
        raise Exception("Current version is not tagged, you can only reproduce an experiment from a tagged version.")

def currentVersionIsTagged() -> bool:
    return currentTag in tags

def fileExists(fileName) -> bool:
    return os.path.exists(fileName)

def folderExists(folderName) -> bool:
    return os.path.isdir(folderName)

def searchForInputFolder() -> None:
    global inputFolder
    print("Searching for input folder...")
    if folderExists("inputs"):
        inputFolder = "inputs/"
        print(f"{path}{inputFolder} found !")
    else:
        raise Exception(f"{path}/inputs folder does not exist")

def searchForOutputFolder() -> None:
    global outputFolder
    answer = input("Where are the outputs generated ? Give the path from the root of the repository : ")
    if answer == "":
        warnings.warn("No output folder given, no output files will be registered")
    else:
        if not folderExists(answer):
            raise Exception(f"{answer} folder does not exist")
        else:
            if not answer.endswith("/"):
                answer+="/"
            outputFolder = answer

def searchForParamsFolder() -> None:
    global paramsFolder
    if folderExists("params"):
        paramsFolder = "params"
    else:
        raise Exception(f"{path}/params folder does not exist")

def askForCommandsFile() -> None:
    global commandsFile
    commandsFile = input("Enter the name of the commands file: ")
    if commandsFile == "":
        raise Exception("No commands file given")
    if not fileExists(commandsFile):
        raise Exception(f"{commandsFile} file does not exist")

def captureExperiment() -> None :
    print("Capturing commands in terminal, when the experiment is done, type \"done\"")
    inputs = []
    userInput = input()
    while (userInput != "done"):
        inputs.append(userInput)
        process = subprocess.run(userInput, shell=True)
        process.check_returncode()
        userInput = input()
    print(f"Done recording the experiment, writing commands in a {commandsFile} file")
    registeringExperimentInputs(inputs)

def registeringExperimentInputs(inputs) -> None:
    with open(commandsFile, "w") as file:
        for input in inputs:
            file.write(input+"\n")


def runExperiment() -> None:
    print("Trying to run experiment")
    file = open(commandsFile, "r")
    for line in file.read().splitlines():
        print(f"running {line} ...")
        process = subprocess.run(line,shell=True)
        process.check_returncode()
        print("done")

def scanInputFiles() -> None:
    for file in os.listdir(inputFolder):
        if not file.endswith(".gitkeep"):
            inputFiles.append(f"{inputFolder}{file}")

def scanOutputsGenerated() -> None:
    for file in os.listdir(outputFolder):
        if not file.endswith(".gitkeep"):
            outputFiles.append(f"{outputFolder}{file}")

def checkGeneratedFiles() -> None : 
    changesNotAdded = [ item.a_path for item in repository.index.diff(None) ]
    untrackedFiles = repository.untracked_files
    if collections.Counter(outputFiles + inputFiles) != collections.Counter(untrackedFiles + changesNotAdded):
        raise Exception("There were files generated or modified outside the input and output folders")

def writeInYaml() -> None:
    with open(EXPERIMENT_RESUME, "r") as yamlFile:
        cur_yaml = yaml.safe_load(yamlFile)
        cur_yaml.update({"name":experimentName})
        cur_yaml.update({"commands":commandsFile})
        cur_yaml.update({"inputs":inputFiles})
        cur_yaml.update({"outputs":outputFiles})
        checksums = {"checksums":genChecksums()}
        cur_yaml.update(checksums)
    with open('experimentResume.yaml', 'w') as yamlFile:
        yaml.safe_dump(cur_yaml, yamlFile)

def successfullyCreatedNewBranch(name) -> bool :
    try:
        repository.git.checkout('-b',name)
        return True
    except Exception as e:
        return False

def pushBranch(version=1) -> None:
    print("Pushing branch...")
    while not(successfullyCreatedNewBranch(f"{experimentName}Experiment{version}")):
        version += 1
    newTag = f"{currentTag}-e{version}"
    print(f"creating {experimentName}Experiment{version} branch and pushing changes to it ...")
    repository.git.add(all=True)
    repository.git.commit(m=f"{experimentName}Experiment{version}")
    repository.git.push('--set-upstream',repository.remote().name,f"{experimentName}Experiment{version}")
    repository.git.tag(newTag)
    repository.git.push('origin',newTag)
    repository.git.checkout(experimentName)
    print("done")

def genChecksum(file) -> str :
    hash_md5 = hashlib.md5()
    with open(file, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def genChecksums() -> list[dict]:
    checksums = []
    for file in outputFiles:
        checksums.append({file : genChecksum(file)})
    return checksums

def run(folder) -> None :
    init(folder)
    repository.active_branch.checkout()
    searchForInputFolder()
    searchForOutputFolder()
    searchForParamsFolder()
    userInput = input("Do you have a pre-recorded commands file? (y/n)")
    if userInput == "y":
        askForCommandsFile()
        runExperiment()
    else:
        captureExperiment()
    scanInputFiles()
    if outputFolder != None :
        scanOutputsGenerated()
    checkGeneratedFiles()
    writeInYaml()
    #pushBranch()