from graphviz import Digraph
from revuz import DFA, State
from pathlib import Path
import os

class TupleState:
    def __init__(self, id: tuple[int, int], sentinel: "TupleState | None", successors: dict[str, "TupleState"] | None = None):
        if successors is None:
            successors = {}
        for char in successors:
            assert len(char) == 1
        self.succ = successors
        self.id = id
        # if sentinel is None, then final has to be false, because this state
        #   (self) is the sentinel state (which can never be final)
        self.sentinel = sentinel if sentinel else self
        self.parents: dict["TupleState", set[str]] = {}
        # a height of -1 means the height of this state is undefined.
        self.height = -1

    def add_succ(self, char: str, succ: "TupleState"):
        assert char not in self.succ
        assert len(char) == 1
        self.succ[char] = succ

    def update_succ(self, char: str, succ: "TupleState"):
        assert char in self.succ
        assert len(char) == 1
        self.succ[char] = succ

    def add_parent(self, parent: "TupleState", character: str):
        if parent in self.parents:
            self.parents[parent].add(character)
        else:
            self.parents[parent] = set([character])

    def set_height(self, height: int):
        self.height = max(self.height, height)

    def next(self, char: str):
        assert len(char) == 1
        return self.succ.get(char, self.sentinel)

    def __repr__(self):
        return "State(" + str(self.id) + ")"

    def __str__(self):
        return str(self.id)

class DFCA:
    def __init__(self):
        self.l = 0
        self.n = 0
        self.S = {}
        self.D = []
        self.state_to_i_in_D = {}
        self.alphabet = set()

    def from_lang(self, language: set[str]):
        dfa = DFA()
        self.l = max(map(len, language)) if len(language) > 0 else 0
        for word in language:
            self.alphabet.update(word)
        dfa.from_lang(language)
        dfa.revuz()

        self.sentinels: list[TupleState] = []
        for i in range(self.l + 1, 0, -1):
            self.sentinels.append(TupleState((dfa.sentinel.id, i), self.sentinels[-1] if len(self.sentinels) > 0 else None))
        self.sentinels.reverse() # the states [(s, 1), ... , (s, l + 1)] where s represents the sentinel state in the original dfa. We don't need (s, 0) because we assume the initial state is not a sink
        # therefore self.sentinels[i] corresponds to the state (s, i + 1)
        minimal_sentinel_touched = len(self.sentinels) - 1
        self.initial = TupleState((0,0), self.sentinels[0], {})
        self.allstates: set[TupleState] = set([self.initial] + self.sentinels)
        self.tuple_to_state = {s.id: s for s in self.allstates}
        self.finalstates: set[TupleState] = set()

        self.n = dfa.sentinel.id + 1


        def traverse(initial: State, depth = 0) -> TupleState:
            nonlocal dfa, self, minimal_sentinel_touched
            # NOTE: if there is a cycle in the dfa, this function does not terminate
            sid = (initial.id, depth)
            if sid in self.tuple_to_state:
                newstate = self.tuple_to_state[sid]
            else:
                newstate = TupleState(sid, self.sentinels[depth], {})
                self.tuple_to_state[sid] = newstate
                self.allstates.add(newstate)
            if initial in dfa.finalstates:
                self.finalstates.add(newstate)
            chars = set(self.alphabet)
            for char in initial.succ:
                s = traverse(initial.succ[char], depth + 1)
                newstate.succ[char] = s
                s.add_parent(newstate, char)
                chars.remove(char)
            if chars:
                minimal_sentinel_touched = min(minimal_sentinel_touched, depth)
            return newstate

        traverse(dfa.initial)

        # cleanup unreachable sentinel states
        for i in range(minimal_sentinel_touched):
            del self.tuple_to_state[self.sentinels[i].id]
            self.allstates.remove(self.sentinels[i])
        self.sentinels = self.sentinels[minimal_sentinel_touched:]
        # If the language is empty, the sentinels must also include the initial state
        if len(language) == 0:
            self.sentinels.append(self.initial)

    def decode(self):
        res = set()
        def traverse(state: TupleState, prefix: str):
            nonlocal res
            min_dist = self.state_to_i_in_D[state.id]
            if min_dist == -1: # we are in a sink state
                return
            if min_dist == 0: # we are in a final state
                res.add(prefix)
            if len(prefix) > self.l - min_dist or len(prefix) == self.l:
                return
            for char in state.succ:
                next_state = state.succ[char]
                traverse(next_state, prefix + char)
        traverse(self.initial, "")
        return res


    def visualize(self):
        dot = Digraph()
        for state in self.allstates:
            iden = str(state)
            dot.node(iden, iden, peripheries="2" if state in self.finalstates else "1")
        for state in self.allstates:
            iden = str(state)
            mapping: dict[TupleState, set[str]] = {}
            for char in self.alphabet:
                succ = state.next(char)
                if succ in mapping:
                    mapping[succ].add(char)
                else:
                    mapping[succ] = set(char)
            for succ in mapping:
                dot.edge(str(state), str(succ), str(",".join(mapping[succ])))
        dot.render(view=True)

    def calc_D(self) -> list[set[tuple[int, int]]]:
        current_states: set[TupleState] = set(self.finalstates)
        dist_to_final = 0
        self.D = [set() for _ in range(self.l + 2)]
        visited: set[TupleState] = set()
        while len(current_states) > 0:
            next_states = set()
            while len(current_states) > 0:
                q = current_states.pop()
                if q in visited:
                    continue
                visited.add(q)
                assert dist_to_final <= self.l
                self.D[dist_to_final + 1].add(q.id) # TODO add bounds check here as assertion
                for parent in q.parents:
                    if parent in visited:
                        continue
                    next_states.add(parent)
            current_states = set(next_states)
            dist_to_final += 1

        self.D[0] = set(map(lambda x: x.id, self.sentinels)) # D_(-1)

        return self.D

    def calc_S(self):
        # step 1
        self.calc_D()
        self.state_to_i_in_D: dict[tuple[int, int], int] = {}
        for i in range(len(self.D)):
            for state in self.D[i]:
                self.state_to_i_in_D[state] = i - 1

        self.S: dict[tuple[int, int], set[TupleState]] = {}
        # step 2z (I made this one up)
        for t in self.tuple_to_state:
            self.S[t] = set([self.tuple_to_state[t]])
        # step 2a
        for i in range(self.l+1):
            tid1 = (self.n-1, i)
            if tid1 not in self.tuple_to_state:
                continue
            for j in range(i, self.l + 2):
                tid2 = (self.n-1, j)
                if tid2 not in self.tuple_to_state:
                    continue
                self.update_similarity(tid1, tid2)
        # step 2b
        for i in range(self.l+1):
            tid = (self.n - 1, self.l + 1 - i)
            if tid not in self.tuple_to_state:
                continue
            for j in range(i, self.l + 1):
                for alpha in self.D[j + 1]: # careful! off by one error if not adding 1
                    if alpha == tid:
                        continue
                    self.update_similarity(alpha, tid)
        # step 3
        lists: list[list[tuple[int, int]]] = [[] for _ in range(self.l + 2)]
        # step 4
        for alpha in reversed(self.states_ordered()):
            if alpha[0] == self.n - 1:
                continue
            i = self.state_to_i_in_D[alpha]
            for beta in lists[i + 1]:
                similar = True
                for char in self.alphabet:
                    beta_n = self.tuple_to_state[beta].next(char).id
                    alpha_n = self.tuple_to_state[alpha].next(char).id
                    if not self.similar(beta_n, alpha_n):
                        similar = False
                        break
                if similar:
                    self.update_similarity(beta, alpha)
            lists[i + 1].append(alpha)

        print("similarity sets")
        for s in self.S:
            print(f"S_{s}: {self.S[s]}")
        return self.S

    def minimize(self):
        S = self.calc_S()
        i = 0
        q = [(0, 0)]
        T = {t: None for t in self.states_ordered()}
        while True:
            for state in self.S[q[-1]]:
                if state.id in T:
                    del T[state.id]
            if len(T) == 0:
                break
            i += 1
            q_i = next(iter(T))
            q.append(q_i)
        m = i
        self.allstates = set(map(lambda x: self.tuple_to_state[x], q))
        for state in set(self.finalstates):
            if state not in self.allstates:
                self.finalstates.remove(state)
        for q_i in q:
            for char in self.alphabet:
                q_i_state = self.tuple_to_state[q_i]
                successor = q_i_state.next(char)
                if char in q_i_state.succ:
                    del q_i_state.succ[char]
                for j in range(m + 1):
                    if successor in self.S[q[j]]:
                        q_i_state.add_succ(char, self.tuple_to_state[q[j]])
                        break

    def update_similarity(self, tid1: tuple[int, int], tid2: tuple[int, int]):
        if less(tid1, tid2) or tid1 == tid2:
            if tid1 in self.S:
                self.S[tid1].add(self.tuple_to_state[tid2])
            else:
                self.S[tid1] = set([self.tuple_to_state[tid2]])
        if less(tid2, tid1) or tid2 == tid1:
            if tid2 in self.S:
                self.S[tid2].add(self.tuple_to_state[tid1])
            else:
                self.S[tid2] = set([self.tuple_to_state[tid1]])

    def similar(self, tid1: tuple[int, int], tid2: tuple[int, int]):
        if tid1 == tid2: return True
        if less(tid1, tid2):
            return self.tuple_to_state[tid2] in self.S[tid1]
        return self.tuple_to_state[tid1] in self.S[tid2]

    def states_ordered(self):
        # This is stupid, but I have slept too little to make this less janky
        def swap(t: tuple[int, int]):
            return (t[1], t[0])
        return list(map(swap, sorted(map(swap, self.tuple_to_state)))) # sort the states in the order definied by the paper

    def to_file(self, filename: Path, source: Path | None = None):
        print(f"saving dfca to files starting with \"{filename}\"")
        # TODO implement simplification of states (from tuples to numbers)
        tuple_to_number = {(0, 0): 0}
        counter = 1
        with open(filename.with_suffix(".dfca"), "w") as f:
            transition_func: list[tuple] = []
            for state in self.allstates:
                if state.id not in tuple_to_number:
                    tuple_to_number[state.id] = counter
                    counter += 1
                for char in self.alphabet:
                    next_tuple = state.next(char).id
                    if next_tuple not in tuple_to_number:
                        tuple_to_number[next_tuple] = counter
                        counter += 1
                    transition_func.append((tuple_to_number[state.id], char, tuple_to_number[next_tuple]))
            f.writelines([
                "DFCA\n",
                str(self.l) + "\n",
                ",".join(map(lambda x: str(tuple_to_number[x.id]), self.allstates)) + "\n",
                ",".join(map(str, transition_func)) + "\n"])
        with open(filename.with_suffix(".source"), "w") as f:
            if source is None:
                f.writelines(map(lambda x: x + "\n", self.decode()))
            else:
                print("TODO case when source defined for to_file()")

def less(tup1: tuple[int, int], tup2: tuple[int, int]):
    return tup1[1] <= tup2[1] if tup1[1] != tup2[1] else tup1[0] <= tup2[0]

def randomized(**kwargs):
    output: str | None = kwargs["outputlocation"]
    output_path: Path | None = None
    if output:
        if not os.path.isdir(output):
            print("--outputlocation must be a directory if the randomized subcommand is used")
            exit(1)
        output_path = Path(output)
    import random
    random.seed(42)
    alphabet = "ab"
    num_states_dfa = 0
    num_states_dfca = 0
    num_states_prefixtree = 0
    num_langs = 0
    for i in range(100):
        l = set()
        for _ in range(random.randint(50, 100)):
            wordlen = random.randint(5, 10)
            word = ""
            for _ in range(wordlen):
                word += alphabet[random.randint(0, len(alphabet) - 1)]
            l.add(word)
        # l = {'baa', '', 'baaba', 'bbbbb'}
        # l = {'a', 'b', 'ab', 'aab'}
        # l = {'', 'ab', 'abab', 'ababab', 'ababa'}
        print("=== Case begin ===")
        print(f"language: {l}")
        res = run_algos(l, output_path / f"rand_test_{i}" if output_path else None)
        if res:
            states_prefixtree, states_dfa, states_dfca = res
            num_states_prefixtree += states_prefixtree
            num_states_dfa += states_dfa
            num_states_dfca += states_dfca

        num_langs += 1
    print("object      | avg number of states")
    print(f"Prefix-Tree | {num_states_prefixtree/num_langs:3.1f}")
    print(f"min. DFA    | {num_states_dfa/num_langs:3.1f}")
    print(f"min. DFCA   | {num_states_dfca/num_langs:3.1f}")

def from_directory(directory: str, **kwargs):
    print(f"TODO from_directory({directory, kwargs})")
    pass

def from_args(arg: list[str], **kwargs):
    output_path: str | None = kwargs["outputlocation"]
    run_algos(set(arg), Path(output_path) if output_path is not None else None)

def run_algos(lang: set[str], output_path: Path | None) -> tuple[int, int, int] | None:
    dfa = DFA()
    dfa.from_lang(lang)
    states_prefixtree = len(dfa.allstates)
    dfa.revuz()
    l_revuz = dfa.lang()
    states_dfa = len(dfa.allstates)
    dfca = DFCA()
    dfca.from_lang(lang)
    # dfca.visualize()
    dfca.minimize()
    l_revuz = dfa.lang()
    states_dfca = len(dfca.allstates)
    l_dfca = frozenset(dfca.decode())
    if l_dfca != frozenset(lang) or l_revuz != frozenset(lang):
        print(f"error: decoding the dfca of language l = {lang} did not result in l")
        return None

    if output_path:
        dfca.to_file(output_path)

    if states_dfca > states_dfa:
        dfa.visualize()
        dfca.visualize()
        dfca.to_file(Path("suspicious.dfca"))
        input("For the visualized DF(C)As, the minimal DFA is smaller than the corresponding \"minimal\" DFCA..")
    return states_prefixtree, states_dfa, states_dfca


def main():
    from argparse import ArgumentParser
    parser = ArgumentParser()
    subparsers = parser.add_subparsers(required=True)
    parser_random = subparsers.add_parser("randomized")
    parser_dir = subparsers.add_parser("from-directory")
    parser_arg = subparsers.add_parser("from-arg")
    parser_random.set_defaults(func=randomized)
    parser_dir.add_argument("directory", type=str)
    parser_dir.set_defaults(func=from_directory)
    parser_arg.add_argument("arg", nargs="*")
    parser_arg.set_defaults(func=from_args)
    parser.add_argument("-o", "--outputlocation", type=str)
    args = parser.parse_args()
    args.func(**vars(args))

if __name__ == "__main__":
    main()