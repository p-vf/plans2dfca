import networkx as nx
import argparse
from pyvis.network import Network
import shutil
import os
import sys

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dot-file")
    args = parser.parse_args()
    directory = vars(args)["dot-file"]
    # Confusingly, nt.write_html generates a superfluous folder called "./lib"
    # Therefore, we check if there is a folder with this name in this directory
    # already, as there could be strange interactions
    if os.path.exists("./lib"):
        print("Fatal error while visualizing: folder \"./lib\" already exists", file=sys.stderr)
        exit(1)
    g = nx.DiGraph(nx.nx_pydot.read_dot(directory))
    nt = Network(directed=True)
    nt.from_nx(g)
    nt.show_buttons()
    nt.write_html("dfca.html")
    shutil.rmtree("./lib")

if __name__ == "__main__":
    main()
