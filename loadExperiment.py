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

inputFiles = []

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
    global commandsFile, inputFiles, outputFiles, beforeHash
    if not (os.path.exists('experimentResume.yaml')):
        raise Exception("No exeperimentResume.yaml file found, the branch is not an exeperiment")
    with open('experimentResume.yaml', 'r') as stream:
        parameters = yaml.safe_load(stream)
        commandsFile = parameters.get('commands')
        outputFiles = parameters.get('outputs')
        inputFiles = parameters.get('inputs')
        beforeHash = parameters.get('checksums')

def runExperiment() -> None :
    file = open(commandsFile, "r")
    for line in file.read().splitlines():
        print(f"running {line} ...")
        process = subprocess.run(line,shell=True)
        process.check_returncode()
        print("done")


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
            checksums.append({file : genChecksum(f'outputs/{file}')})
    return checksums


def compareChecksums() -> bool:
    changes = False
    for (dict1, dict2) in zip(beforeHash, genChecksums()):
        for (key, value) in dict1.items():
            if dict2.get(key) != value :
                warnings.warn(f"{OUTPUT_FOLDER}/{key} has changed")
                changes = True
    return changes


def run(repository, branch) -> None :
    print("Initializing the experiment repository ...")
    init(repository, branch)
    print("Getting the experiment parameters ...")
    getParameters()
    print("Running the experiment ...")
    runExperiment()
    print("Comparing checksums of the outputs ...")
    if (compareChecksums()) : 
        print("The exepriment was reproduced with succes but some output files are differents.")
    else :
        print("The exepriment was reproduced with succes !")
    
#TODO : laisser à l'utilisateur le temps de reproduire l'experience