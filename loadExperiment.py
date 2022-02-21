import git
import os
import subprocess
import yaml
import hashlib
import warnings

INPUT_FOLDER = "inputs"
OUTPUT_FOLDER = "outputs"

repo = None
folder = None

commandsFile = None
instructionFile = None

inputFiles = []
outputFiles = []

dockerfileIsPresent = False
beforeHash = None

def init(repository,branch) -> None :
    global repo, folder
    folder = repository.split('/')[-1].split('.')[0]
    if os.path.exists(folder) :
        print(f"Folder ./{folder} already exists, do you want to delete it ? (y/n)")
        answer = input()
        if answer == 'y' :
            os.system(f"rm -rf ./{folder}")
        else :
            print("Aborting")
            exit(0)
    git.Git("./").clone(repository)
    repo = git.Repo(folder)
    try : 
        repo.git.checkout(branch)
    except git.exc.GitCommandError : 
        raise Exception(f"Branch {branch} not found in the repository")
    os.chdir(folder)

def getParameters() -> None :
    global commandsFile, inputFiles, outputFiles, beforeHash, instructionFile, dockerfileIsPresent
    if not (os.path.exists('experimentResume.yaml')):
        raise Exception("No exeperimentResume.yaml file found, the branch is not an exeperiment")
    with open('experimentResume.yaml', 'r') as stream:
        parameters = yaml.safe_load(stream)
        commandsFile = parameters.get('commands')
        outputFiles = parameters.get('outputs')
        inputFiles = parameters.get('inputs')
        beforeHash = parameters.get('checksums')
        instructionFile = parameters.get('instructions')
        dockerfileIsPresent = parameters.get('dockerfile')


def runExperiment() -> None :
    file = open(commandsFile, "r")
    for line in file.read().splitlines():
        print(f"running {line} ...")
        process = subprocess.run(line,shell=True)
        process.check_returncode()
        print("done")

def checkForInstructions() -> None :
    if (instructionFile != None) :
        print("You can check the instructions for the experiment in the file : " + instructionFile)
    else :
        warnings.warn("No instructions for the experiment found in the repository")
    print("Run the exepriment and then press enter when it's done")
    done = "nope"
    while (done != "") :
        done = input()

def genChecksum(file) -> str :
    hash_md5 = hashlib.md5()
    with open(file, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def genChecksums() -> list[dict]:
    checksums = []
    for file in os.listdir(OUTPUT_FOLDER) :
        if not file.endswith(".gitkeep"):
            checksums.append({f"{OUTPUT_FOLDER}/{file}" : genChecksum(f'{OUTPUT_FOLDER}/{file}')})
    return checksums


def compareChecksums() -> bool:
    changes = False
    for (dict1, dict2) in zip(beforeHash, genChecksums()):
        for (key, value) in dict1.items():
            if dict2.get(key) != value :
                warnings.warn(f"{key} has changed")
                changes = True
    return changes


def buildDockerImage() -> None:
    print("Building the docker image ...")
    try :
        subprocess.run(f"docker build -t experimentreproduction ./",shell=True).check_returncode()
    except :
        subprocess.run(f"sudo docker build -t experimentreproduction ./",shell=True).check_returncode()

def getWorkir() -> str :
    workdir = "/" 
    with open("Dockerfile","r") as file:
        for line in file.read().splitlines():
            if line.startswith("WORKDIR"):
                workdir = line.split(" ")[1]
    return workdir

def runDockerImage() -> None:
    print("binding docker image to the current directory and running it...")
    try:
        subprocess.run(f"docker run -it --mount type=bind,source=\"$PWD\",target={getWorkir()} experimentreproduction",shell=True).check_returncode()
    except :
        subprocess.run(f"sudo docker run -it --mount type=bind,source=\"$PWD\",target={getWorkir()} experimentreproduction",shell=True).check_returncode()


def run(repository, branch) -> None :
    print("Initializing the experiment repository ...")
    init(repository, branch)
    print("Getting the experiment parameters ...")
    getParameters()
    print("Running the experiment ...")
    if (dockerfileIsPresent) :
        print("Dockerimage was found ! Using it to run the experiment...")
        buildDockerImage()
        runDockerImage()
    else:
        if (commandsFile != None) : 
            runExperiment()
        else :
            checkForInstructions()
    print("Comparing checksums of the outputs ...")
    if (compareChecksums()) : 
        print("The exepriment was reproduced with succes but some output files are differents.")
    else :
        print("The exepriment was reproduced with succes !")