import argparse
import registerExperiment
import loadExperiment

if (__name__ == "__main__"):
    parser = argparse.ArgumentParser(description="Reproduction tool")
    g = parser.add_mutually_exclusive_group()
    g.add_argument("-s", "--save", help="Register a new experiment from a local git repository")
    g.add_argument("-l", "--load", help="Reproduce an experiment from a distant git repository")
    parser.add_argument("-b", "--branch", help="Branch to use for the experiment")
    args = parser.parse_args()

    if args.save:
        registerExperiment.run(args.save)
    if args.load:
        if not (args.branch):
            print("Please specify a branch")
            exit(1)
        loadExperiment.run(args.load, args.branch)
    if (not args.save) and (not args.load):
        print("Please specify an action")
        exit(1)