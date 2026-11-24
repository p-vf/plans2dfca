import argparse
from pyvis.network import Network
import os

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory")
    parser.add_argument("zip-file")
    args = parser.parse_args()
    zip_file = vars(args)["zip-file"]
    directory = vars(args)["directory"]
    with open("num_states.csv", "a+") as f:
        zipped_plans_size = os.stat(zip_file).st_size
        unzipped_plans_size = 0
        num_plans = 0
        for p in os.listdir(directory):
            num_plans += 1
            unzipped_plans_size += os.stat(os.path.join(directory, p)).st_size
        f.write(f"zipped_plans_size,{zipped_plans_size}\n")
        f.write(f"unzipped_plans_size,{unzipped_plans_size}\n")
        f.write(f"num_plans,{num_plans}\n")

if __name__ == "__main__":
    main()
