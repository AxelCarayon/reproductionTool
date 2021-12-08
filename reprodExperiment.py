import argparse
import registerExperiment

if (__name__ == "__main__"):
    parser = argparse.ArgumentParser(description="Reproduction tool")
    g = parser.add_mutually_exclusive_group()
    g.add_argument("-s", "--save", help="Register a new experiment from a local git repository")
    g.add_argument("-l", "--load", help="Reproduce an experiment")
    args = parser.parse_args()

    if args.save:
        registerExperiment.run(args.save)
    if args.load:
        #TODO
        pass