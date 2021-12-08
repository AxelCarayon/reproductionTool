import os
import git
import subprocess
import yaml
import hashlib

path = "./"

repository = None

inputFolder = None
inputFiles = []

paramsFolder = None

commandsFile = None

experimentName = None

outputFolder = None
outputFiles = []

def isGitRepo(path) -> bool:
    try:
        git.Repo(path)
        return True
    except git.exc.InvalidGitRepositoryError:
        return False
def init(pathInput) -> None :
    global repository,path,experimentName
    if isGitRepo(pathInput):
        path += pathInput
        if not (pathInput[len(pathInput)-1] == "/"):
            path+="/"
        repository = git.Repo(path)
        experimentName = repository.active_branch.name
        os.chdir(path)
    else :
        raise Exception(f"{pathInput} is not a git repository")

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
    print("Searching for output folder...")
    if folderExists("outputs"):
        outputFolder = "outputs/"
        print(f"{path}{outputFolder} found !")
    else:
        raise Exception(f"{path}/outputs folder does not exist")

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
            inputFiles.append(file)

def scanOutputsGenerated() -> None:
    for file in os.listdir(outputFolder):
        if not file.endswith(".gitkeep"):
            outputFiles.append(file)

def writeInYaml() -> None:
    with open("experimentResume.yaml", "r") as yamlFile:
        cur_yaml = yaml.safe_load(yamlFile)
        cur_yaml.update({"name":experimentName})
        cur_yaml.update({"commands":commandsFile})
        cur_yaml.update({"inputs":inputFiles})
        cur_yaml.update({"outputs":outputFiles})
        checksums = {"checksums":genChecksums()}
        cur_yaml.update(checksums)
    with open('experimentResume.yaml', 'w') as yamlFile:
        yaml.safe_dump(cur_yaml, yamlFile)

def branchExists(branchName) -> bool:
    return branchName in repository.references

def pushBranch(version=1) -> None:
    while (branchExists(f"{experimentName}Experiment{version}")):
        version += 1
    else:
        repository.git.checkout('-b', f"{experimentName}Experiment{version}")
        repository.git.add(all=True)
        repository.git.commit(m=f"{experimentName}Experiment{version}")
        repository.git.push('--set-upstream', repository.remote().name, f"{experimentName}Experiment{version}")
        repository.git.checkout(experimentName)

def genChecksum(file) -> str :
    hash_md5 = hashlib.md5()
    with open(file, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def genChecksums() -> list[dict]:
    checksums = []
    for file in outputFiles:
        checksums.append({file : genChecksum(outputFolder+file)})
    return checksums

def run(folder) -> None :
    init(folder)
    repository.active_branch.checkout()
    searchForInputFolder()
    searchForOutputFolder()
    searchForParamsFolder()
    askForCommandsFile()
    runExperiment()
    scanInputFiles()
    scanOutputsGenerated()
    writeInYaml()
    pushBranch()