from multiprocessing.connection import answer_challenge
import os
from unicodedata import name
import git
import subprocess
import yaml
import hashlib
import warnings

EXPERIMENT_RESUME = "experimentResume.yaml"
DOCKERFILE = "Dockerfile"

path = "./"

repository = None

inputFolder = None
inputFiles = []

paramsFolder = None
paramsFiles = []

commandsFile = None
instructionFile = None

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



def dockerfileIsPresent() -> bool:
    if fileExists(DOCKERFILE):
        answer = input("A dockerfile was found ! It will be used to reproduce the experiment. Is that ok for you ? (y/n)")
        if answer == "n":
            raise Exception("""Remove the dockerfile and try again""")
        return True
    else :
        return False

def buildDockerImage() -> None:
    print("Building the docker image ...")
    try :
        subprocess.run(f"docker build -t {experimentName.lower()}experiment ./",shell=True).check_returncode()
    except :
        subprocess.run(f"sudo docker build -t {experimentName.lower()}experiment ./",shell=True).check_returncode()

def getWorkir() -> str :
    workdir = "/" 
    with open(DOCKERFILE,"r") as file:
        for line in file.read().splitlines():
            if line.startswith("WORKDIR"):
                workdir = line.split(" ")[1]
    return workdir

def runDockerImage() -> None:
    print("binding docker image to the current directory and running it...")
    try:
        subprocess.run(f"docker run -it --mount type=bind,source=\"$PWD\",target={getWorkir()} {experimentName.lower()}experiment",shell=True).check_returncode()
    except :
        subprocess.run(f"sudo docker run -it --mount type=bind,source=\"$PWD\",target={getWorkir()} {experimentName.lower()}experiment",shell=True).check_returncode()
    #TODO : vérifier si la reproduction avec un Dockerfile marche dans l'autre sens

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

def askForInputFolder() -> None:
    global inputFolder
    answer = input("If you use input data, where are they stored ? Give the path from the root of the repository : ")
    if answer == "":
        warnings.warn("No input folder given, no input files will be registered")
    else:
        if not folderExists(answer):
            raise Exception(f"{path}/{answer} folder does not exist")
        else:
            if not answer.endswith("/"):
                answer+="/"
            inputFolder = answer

def askForOutputFolder() -> None:
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

def askForParamsFolder() -> None:
    global paramsFolder
    answer = input("In which folder do you store your parameters ? Give the path from the root of the repository : ")
    if answer == "":
        warnings.warn("No parameters folder given, no parameters will be registered")
    else:
        if not folderExists(answer):
            raise Exception(f"{path}/{answer} folder does not exist")
        else:
            if not answer.endswith("/"):
                answer+="/"
            paramsFolder = answer

def askForCommandsFile() -> None:
    global commandsFile
    commandsFile = input("Enter the name of the commands file: ")
    if not fileExists(commandsFile):
        raise Exception(f"{commandsFile} file does not exist")

def askForInstructionFile() -> None :
    global instructionFile
    print("If you have an instruction file, enter its name, otherwise press enter")
    instructionFile = input()
    if instructionFile == "":
        warnings.warn("No instruction file given, make sure you give instructions to reproduce the experiment along with it")
    else:
        if not fileExists(instructionFile):
            raise Exception(f"{instructionFile} file does not exist")

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

def scanParameters() -> None:
    for file in os.listdir(paramsFolder):
        if not file.endswith(".gitkeep"):
            paramsFiles.append(f"{paramsFolder}{file}")

def isNotAnOutputfile(file) -> bool: return file not in outputFiles
def isNotAnInputfile(file) -> bool: return file not in inputFiles
def isNotAParamFile(file) -> bool: return file not in paramsFiles

def checkGeneratedFiles() -> None : 
    editedFiles = [ item.a_path for item in repository.index.diff(None) ]+ [ item.a_path for item in repository.index.diff(repository.head.name) ] + repository.untracked_files
    outOfPlaceFiles = []
    logFile = open("outOfPlaceFiles.log","w")
    for file in editedFiles:
        if  file!=DOCKERFILE and \
            file!=EXPERIMENT_RESUME and \
            isNotAnOutputfile(file) and \
            isNotAnInputfile(file) and \
            isNotAParamFile(file):
            outOfPlaceFiles.append(file)
            logFile.write(f"{file}\n")

    logFile.close()
    if len(outOfPlaceFiles) == 0:
        os.remove("outOfPlaceFiles.log")
    else :
        raise Exception("""Some files modified or created were not registered as input, output or parameter file.
        Thoses files are logged in the file outOfPlaceFiles.log""")


def writeInYaml() -> None:
    with open(EXPERIMENT_RESUME, "r") as yamlFile:
        cur_yaml = yaml.safe_load(yamlFile)
        cur_yaml.update({"name":experimentName})
        cur_yaml.update({"commands":commandsFile})
        cur_yaml.update({"inputs":inputFiles})
        cur_yaml.update({"outputs":outputFiles})
        cur_yaml.update({"params":paramsFiles})
        cur_yaml.update({"instruction":instructionFile})
        cur_yaml.update({"dockerfile":fileExists(DOCKERFILE)})
        checksums = {"checksums":genChecksums()}
        cur_yaml.update(checksums)
    with open(EXPERIMENT_RESUME, 'w') as yamlFile:
        yaml.safe_dump(cur_yaml, yamlFile)


def pushBranch(version=1) -> None:
    print("Pushing branch...")
    while f"{experimentName}Experiment{version}" in repository.remote().refs:
        print(f"{experimentName}Experiment{version} already exists")
        version += 1
    newTag = f"{currentTag}-e{version}"
    print(f"creating {experimentName}Experiment{version} branch and pushing changes to it ...")
    repository.git.checkout(b=f"{experimentName}Experiment{version}")
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


def askFolders() -> None :
    askForInputFolder()
    askForOutputFolder()
    askForParamsFolder()

def reproduceExperiment() -> None:
    if dockerfileIsPresent() :
        buildDockerImage()
        runDockerImage()
    else:
        userInput = input("Do you have a pre-recorded commands file? (y/n)")
        if userInput == "y":
            askForCommandsFile()
            runExperiment()
        else:
            askForInstructionFile()
            done = ""
            while(done != "done"):
                done = input("Run your experiment and then type 'done' when you are done : ")

def scanAfterExecution() -> None:
    if inputFolder != None :
        scanInputFiles()
    if outputFolder != None :
        scanOutputsGenerated()
    if paramsFolder != None :
        scanParameters()

def run(folder) -> None :
    init(folder)
    repository.active_branch.checkout()
    askFolders()
    reproduceExperiment()
    scanAfterExecution()
    checkGeneratedFiles()
    writeInYaml()
    print(f"Please check the {EXPERIMENT_RESUME} file, if everything is correct, press enter to continue, otherwise type \"abort\"")
    if input() == "abort":
        raise Exception("Aborted")
    pushBranch()
