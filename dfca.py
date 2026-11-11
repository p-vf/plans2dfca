from graphviz import Digraph
from revuz import DFA, State, group_str
from pathlib import Path
from collections import deque
from typing import cast
import math
import os

class TupleState:
    def __init__(self, id: tuple[int, int], sentinel: "TupleState | None", successors: dict[int, "TupleState"] | None = None):
        if successors is None:
            successors = {}
        self.succ = successors
        self.id = id
        # if sentinel is None, then final has to be false, because this state
        #   (self) is the sentinel state (which can never be final)
        self.sentinel = sentinel if sentinel else self
        self.parents: dict["TupleState", set[int]] = {}
        # a height of -1 means the height of this state is undefined.
        self.height = -1

    def add_succ(self, char: int, succ: "TupleState"):
        # either this node has no successor for this character or the successor is the same
        assert char not in self.succ or self.succ[char] == succ
        self.succ[char] = succ

    def update_succ(self, char: int, succ: "TupleState"):
        assert char in self.succ
        self.succ[char] = succ

    def add_parent(self, parent: "TupleState", character: int):
        if parent in self.parents:
            self.parents[parent].add(character)
        else:
            self.parents[parent] = set([character])

    def set_height(self, height: int):
        self.height = max(self.height, height)

    def next(self, char: int):
        return self.succ.get(char, self.sentinel)

    def __repr__(self):
        return "State(" + str(self.id) + ")"

    def __str__(self):
        return str(self.id)

class DFCA:
    def __init__(self):
        self.l = 0
        self.alphabet: list[int] = []
        self.initial: State | None = None
        self.allstates: set[State] = set()
        self.finalstates: set[State] = set()

        # Mapping from state to the minimal length of a word that leads to a final state
        # Required for efficiently decoding the language that this DFCA represents
        self.min_length_to_final: dict[State, int] = {}

    def from_lang(self, lang: set[tuple[int, ...]]):
        minimizer = dfcaMinimizer()
        minimizer.from_lang(lang)
        minimizer.minimize()
        self.from_minimizer(minimizer)

    def from_minimizer(self, minimizer: "dfcaMinimizer"):
        count = 1
        visited: set[TupleState] = set()
        sentinel = State(len(minimizer.allstates) - 1, None, False)
        self.allstates.add(sentinel)
        queue: deque[TupleState] = deque([minimizer.initial])
        tuple_state_to_state: dict[TupleState, State] = {minimizer.initial: State(0, sentinel, minimizer.initial in minimizer.finalstates)}

        # translate the tuple-automaton to a normal one
        while queue:
            tuplestate = queue.popleft()
            if tuplestate in visited:
                continue
            new_state = tuple_state_to_state[tuplestate]
            self.allstates.add(new_state)
            for char in minimizer.alphabet:
                succ = tuplestate.next(char)
                if succ in minimizer.sentinels:
                    tuple_state_to_state[succ] = sentinel
                    continue
                if succ not in tuple_state_to_state:
                    new_succ = State(count, sentinel, tuplestate in minimizer.finalstates)
                    count += 1
                    tuple_state_to_state[succ] = new_succ
                else:
                    new_succ = tuple_state_to_state[succ]
                new_state.succ[char] = new_succ
                new_succ.add_parent(new_state, char)
                queue.append(succ)
            if tuplestate in minimizer.finalstates:
                self.finalstates.add(new_state)
            visited.add(tuplestate)
        if sentinel not in visited:
            self.allstates.remove(sentinel)

        self.initial = tuple_state_to_state[minimizer.initial]
        self.l = minimizer.l

        self.alphabet = minimizer.alphabet

        # this is needed to decode this dfca efficiently
        for tuplestate in minimizer.state_to_i_in_D:
            if tuplestate not in tuple_state_to_state:
                continue
            state = tuple_state_to_state[tuplestate]
            self.min_length_to_final[state] = minimizer.state_to_i_in_D[tuplestate]

    def visualize(self, name: str = "DFCA", directory: str = "graphs"):
        dot = Digraph(engine="fdp", name=name, directory=directory)
        dot.graph_attr["maxiter"] = "100"
        for state in self.allstates:
            iden = str(state.id)
            dot.node(iden, iden, peripheries="2" if state in self.finalstates else "1")
        for state in self.allstates:
            iden = str(state.id)
            mapping: dict[State, set[int]] = {}
            for char in state.succ:
                succ = state.next(char)
                if succ in mapping:
                    mapping[succ].add(char)
                else:
                    mapping[succ] = set([char])
            for succ in mapping:
                dot.edge(str(state.id), str(succ.id), group_str(mapping[succ]), _attributes={"decorate":"True", "labelfloat":"True"})
        dot.render(view=True)

    def to_file(self, filename: Path, source: Path | None = None):
        # TODO implement correct json output
        print(f"saving dfca to files starting with \"{filename}\"")
        filename.mkdir(parents=True, exist_ok=True)
        with open(filename/"dfca.json", "w") as f:
            transition_func: list[tuple] = []
            for state in self.allstates:
                for char in self.alphabet:
                    next_tuple = state.next(char).id
                    transition_func.append((state.id, char, next_tuple))
            f.writelines([
                "DFCA\n",
                str(self.l) + "\n",
                ",".join(map(lambda x: str(x.id), self.allstates)) + "\n",
                ",".join(map(str, transition_func)) + "\n"])
        with open(filename/"source.json", "w") as f:
            if source is None:
                f.writelines(map(lambda x: ",".join(map(str, x)) + "\n", self.decode()))
            else:
                print("TODO case when source defined for to_file()")

    def decode(self) -> set[tuple[int, ...]]:
        res: set[tuple[int, ...]] = set()
        assert self.initial is not None
        stack: list[tuple[State, tuple[int, ...]]] = [(self.initial, ())]

        while stack:
            state, prefix = stack.pop()
            min_dist = self.min_length_to_final[state]
            if min_dist == -1:
                continue
            assert (state in self.finalstates) == (min_dist == 0)
            if state in self.finalstates:
                res.add(prefix)
            if len(prefix) > self.l - min_dist or len(prefix) == self.l:
                continue
            for char in state.succ:
                stack.append((state.succ[char], prefix + (char,)))
        return res

class dfcaMinimizer:
    def __init__(self):
        self.l = 0
        self.n = 0
        self.S = {}
        self.D = []
        self.state_to_i_in_D = {}
        self.alphabet: list[int] = []
        self.min_word_to: dict[TupleState, tuple[int, ...]] = {}

    def from_lang(self, language: set[tuple[int, ...]] | set[str]):
        dfa = DFA()
        self.l = max(map(len, language)) if len(language) > 0 else 0
        dfa.from_lang(language)
        self.alphabet = list(dfa.alphabet)
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

        # depth-first traversal to convert dfa into product automaton with B
        # mapping from state to a set of its parents and its depth
        curr_states: list[tuple[State, tuple[TupleState, int] | None, int]] = [(dfa.initial, None, 0)]
        while curr_states:
            curr_state, parent_or_none, depth = curr_states.pop()

            sid = (curr_state.id, depth)
            if sid in self.tuple_to_state:
                newstate = self.tuple_to_state[sid]
            else:
                newstate = TupleState(sid, self.sentinels[depth], {})
                self.tuple_to_state[sid] = newstate
                self.allstates.add(newstate)
            if parent_or_none:
                parent, char = parent_or_none
                newstate.add_parent(parent, char)
                parent.add_succ(char, newstate)

            if curr_state in dfa.finalstates:
                self.finalstates.add(newstate)
            chars = set(self.alphabet)
            for char in curr_state.succ:
                chars.remove(char)
                succ = curr_state.succ[char]
                curr_states.append((succ, (newstate, char), depth + 1))
            if chars:
                minimal_sentinel_touched = min(minimal_sentinel_touched, depth)

        # print(f"{minimal_sentinel_touched = }")

        # cleanup unreachable sentinel states
        for i in range(minimal_sentinel_touched):
            del self.tuple_to_state[self.sentinels[i].id]
            self.allstates.remove(self.sentinels[i])
        self.sentinels = self.sentinels[minimal_sentinel_touched:]
        # If the language is empty, the sentinels must also include the initial state
        if len(language) == 0:
            self.sentinels.append(self.initial)

    def decode(self) -> set[tuple[int, ...]]:
        res = set()
        def traverse(state: TupleState, prefix: tuple[int, ...]):
            nonlocal res
            min_dist = self.state_to_i_in_D[state]
            if min_dist == -1: # we are in a sink state
                return
            if min_dist == 0: # we are in a final state
                res.add(prefix)
            if len(prefix) > self.l - min_dist or len(prefix) == self.l:
                return
            for char in state.succ:
                next_state = state.succ[char]
                traverse(next_state, prefix + (char,))
        traverse(self.initial, ())
        return res

    def visualize(self, name: str = "DFCA-Minimizer", directory: str = "graphs"):
        dot = Digraph(engine="fdp", name=name, directory=directory)
        dot.graph_attr["maxiter"] = "100"
        for state in self.allstates:
            iden = str(state)
            dot.node(iden, iden, peripheries="2" if state in self.finalstates else "1")
        for state in self.allstates:
            iden = str(state)
            mapping: dict[TupleState, set[int]] = {}
            for char in state.succ:
                succ = state.next(char)
                if succ in mapping:
                    mapping[succ].add(char)
                else:
                    mapping[succ] = set([char])
            for succ in mapping:
                dot.edge(str(state), str(succ), group_str(mapping[succ]))
        dot.render(view=True)

    def calc_D(self) -> list[set[TupleState]]:
        current_states: set[TupleState] = set(self.finalstates)
        dist_to_final = 0
        self.D: list[set[TupleState]] = [set() for _ in range(self.l + 2)]
        visited: set[TupleState] = set()
        while len(current_states) > 0:
            next_states = set()
            while len(current_states) > 0:
                q = current_states.pop()
                if q in visited:
                    continue
                visited.add(q)
                assert dist_to_final <= self.l
                self.D[dist_to_final + 1].add(q) # TODO add bounds check here as assertion
                for parent in q.parents:
                    if parent in visited:
                        continue
                    next_states.add(parent)
            current_states = set(next_states)
            dist_to_final += 1

        self.D[0] = set(map(lambda x: x, self.sentinels)) # D_(-1)

        return self.D

    def calc_S(self):
        # step 1
        self.calc_D()
        self.state_to_i_in_D: dict[TupleState, int] = {}
        for i in range(len(self.D)):
            for state in self.D[i]:
                self.state_to_i_in_D[state] = i - 1

        self.S: dict[TupleState, set[TupleState]] = {}
        # step 2z (I made this one up)
        for q in self.allstates:
            self.S[q] = set([q])
        # step 2a
        for i in range(self.l+1):
            tid1 = (self.n-1, i)
            if tid1 not in self.tuple_to_state:
                continue
            for j in range(i, self.l + 2):
                tid2 = (self.n-1, j)
                if tid2 not in self.tuple_to_state:
                    continue
                self.update_similarity(self.tuple_to_state[tid1], self.tuple_to_state[tid2])
        # step 2b
        for i in range(self.l+1):
            tid = (self.n - 1, self.l + 1 - i)
            if tid not in self.tuple_to_state:
                continue
            for j in range(i, self.l + 1):
                for alpha in self.D[j + 1]: # careful! off by one error if not adding 1
                    if alpha == tid:
                        continue
                    self.update_similarity(alpha, self.tuple_to_state[tid])
        # step 3
        lists: list[list[TupleState]] = [[] for _ in range(self.l + 2)]
        # step 4
        for alpha in reversed(self.states_ordered()):
            if alpha.id[0] == self.n - 1:
                continue
            i = self.state_to_i_in_D[alpha]
            for beta in lists[i + 1]:
                similar = True
                for char in self.alphabet:
                    beta_n = beta.next(char)
                    alpha_n = alpha.next(char)
                    if not self.similar(beta_n, alpha_n):
                        similar = False
                        break
                if similar:
                    self.update_similarity(beta, alpha)
            lists[i + 1].append(alpha)

        return self.S

    def minimize(self):
        S = self.calc_S()
        i = 0
        q = [self.initial]
        T = {t: None for t in self.states_ordered()}
        x: list[tuple[int, ...]] = [()]
        while True:
            for state in self.S[q[-1]]:
                if state in T:
                    del T[state]
            if len(T) == 0:
                break
            i += 1
            q_i = next(iter(T))
            q.append(q_i)
            x.append(self.min_word_to_set(self.S[q_i]))
        if verbose:
            print(f"maximal dissimilar sequence: {x}")
        m = i
        self.allstates = set(q)
        for state in set(self.finalstates):
            if state not in self.allstates:
                self.finalstates.remove(state)
        for q_i in q:
            for char in self.alphabet:
                successor = q_i.next(char)
                if char in q_i.succ:
                    del q_i.succ[char]
                for j in range(m + 1):
                    if successor in self.S[q[j]]:
                        q_i.add_succ(char, q[j])
                        break

    def gen_min_words(self):
        curr_states = deque([self.initial])

        self.min_word_to[self.initial] = ()

        def update_minimal_word_for(state, word):
            if state in self.min_word_to:
                self.min_word_to[state] = pseudolexicographical_min(word, self.min_word_to[state])
            else:
                self.min_word_to[state] = word

        while curr_states:
            curr_state = curr_states.pop()
            prefix = self.min_word_to[curr_state]
            chars = set(self.alphabet)
            for char in curr_state.succ:
                succ = curr_state.succ[char]
                chars.remove(char)
                if succ in self.min_word_to and len(self.min_word_to[succ]) <= len(prefix):
                    continue
                curr_states.appendleft(succ)
                word = prefix + (char,)
                update_minimal_word_for(succ, word)
            if chars:
                if curr_state.sentinel in self.min_word_to and len(self.min_word_to[curr_state.sentinel]) <= len(prefix):
                    continue
                curr_states.appendleft(curr_state.sentinel)
                update_minimal_word_for(curr_state.sentinel, prefix + (min(chars),))

    def min_word_to_set(self, states: set[TupleState]) -> tuple[int, ...]:
        assert len(states) >= 1
        if not self.min_word_to:
            self.gen_min_words()
        states_iter = iter(states)
        min_word = self.min_word_to[next(states_iter)]
        for state in states_iter:
            min_word = pseudolexicographical_min(self.min_word_to[state], min_word)
        return min_word

    def update_similarity(self, state1: TupleState, state2: TupleState):
        if less(state1.id, state2.id) or state1 == state2:
            if state1 in self.S:
                self.S[state1].add(state2)
            else:
                self.S[state1] = set([state2])
        if less(state2.id, state1.id) or state2 == state1:
            if state2 in self.S:
                self.S[state2].add(state1)
            else:
                self.S[state2] = set([state1])

    def similar(self, state1: TupleState, state2: TupleState):
        if state1 == state2: return True
        if less(state1.id, state2.id):
            return state2 in self.S[state1]
        return state1 in self.S[state2]

    def states_ordered(self):
        def swap(t: tuple[int, int]):
            return (t[1], t[0])
        return list(sorted(self.allstates, key=lambda x: swap(x.id))) # sort the states in the order definied by the paper

def pseudolexicographical_min(word1: tuple[int, ...], word2: tuple[int, ...]):
    if len(word1) > len(word2):
        return word2
    if len(word2) > len(word1):
        return word1
    # len(word1) == len(word2)
    for i in range(len(word1)):
        if word1[i] > word2[i]:
            return word2
        if word2[i] > word1[i]:
            return word1
    # word1 == word2
    return word1

def less(tup1: tuple[int, int], tup2: tuple[int, int]):
    return tup1[1] <= tup2[1] if tup1[1] != tup2[1] else tup1[0] <= tup2[0]

def int_lang_to_str_lang(lang: set[tuple[int, ...]]):
    res = set()
    for w in lang:
        new_w = ""
        for char in w:
            new_w += chr(char)
        res.add(new_w)
    return res

def str_lang_to_int_lang(lang: set[str]):
    res = set()
    for w in lang:
        new_w: tuple[int, ...] = ()
        for char in w:
            new_w += (ord(char),)
        res.add(new_w)
    return res

def lang_to_int_lang(lang: set[str] | set[tuple[int, ...]]):
    if lang and isinstance(next(iter(lang)), str):
        lang = cast(set[str], lang)
        return str_lang_to_int_lang(lang)
    return lang

def randomized(**kwargs):
    output: str | None = kwargs["outputlocation"]
    output_path: Path | None = None
    visualize: bool = kwargs["visualize"]
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
    minlen = 0
    maxlen = 20
    minsize = 0
    maxsize = 100
    # uniform word-lengths between minlen and maxlen
    for i in range(100):
        l = set()
        for _ in range(random.randint(minsize, maxsize)):
            wordlen = random.randint(minlen, maxlen)
            word = ""
            for _ in range(wordlen):
                word += alphabet[random.randint(0, len(alphabet) - 1)]
            l.add(word)
        if verbose:
            print("=== Case begin ===")
            print(f"language: {l}")
        res = run_algos(l, str(output_path / f"rand_test_{i}") if output_path else None, visualize=visualize)
        if res:
            states_prefixtree, states_dfa, states_dfca = res
            num_states_prefixtree += states_prefixtree
            num_states_dfa += states_dfa
            num_states_dfca += states_dfca

        num_langs += 1
    print("Results uniformly distributed word length:")
    print("object      | avg number of states")
    print(f"Prefix-Tree | {num_states_prefixtree/num_langs:3.1f}")
    print(f"min. DFA    | {num_states_dfa/num_langs:3.1f}")
    print(f"min. DFCA   | {num_states_dfca/num_langs:3.1f}")

    num_states_dfa = 0
    num_states_dfca = 0
    num_states_prefixtree = 0
    num_langs = 0
    # length is not uniformely distributed: more long words, fewer short ones
    exponent = 7
    max_tries_factor = 2 ** exponent
    for i in range(100):
        l = set()
        size = random.randint(minsize, maxsize)
        tries = 0
        while len(l) < size and not tries > max_tries_factor * size:
            wordlen = int(math.pow(random.random() * math.pow(maxlen - minlen, exponent), 1/exponent)) + minlen
            word = ""
            for _ in range(wordlen):
                word += alphabet[random.randint(0, len(alphabet) - 1)]
            l.add(word)
            tries += 1
        if verbose:
            print("=== Case begin ===")
            print(f"language: {l}")
        res = run_algos(l, str(output_path / f"rand_test_{i}") if output_path else None, visualize=visualize)
        if res:
            states_prefixtree, states_dfa, states_dfca = res
            num_states_prefixtree += states_prefixtree
            num_states_dfa += states_dfa
            num_states_dfca += states_dfca

        num_langs += 1
    print("Results non-uniformly distributed word length:")
    print("object      | avg number of states")
    print(f"Prefix-Tree | {num_states_prefixtree/num_langs:3.1f}")
    print(f"min. DFA    | {num_states_dfa/num_langs:3.1f}")
    print(f"min. DFCA   | {num_states_dfca/num_langs:3.1f}")

def from_directory(directory: str, **kwargs):
    d = Path(directory)
    lang: set[tuple[int, ...]] = set()
    line_to_int: dict[str, int] = {}
    counter = 0
    for file in os.listdir(d):
        if not os.path.isfile(d / file):
            continue
        if not file.startswith("sas_plan."):
            continue
        with open(d/file, "r") as f:
            word: tuple[int, ...] = ()
            for line in f:
                if line in line_to_int:
                    char = line_to_int[line]
                else:
                    char = counter
                    line_to_int[line] = char
                    counter += 1
                word += (char,)
        lang.add(word)
    run_algos(lang, kwargs["outputlocation"], kwargs["visualize"])

def from_args(arg: list[str], **kwargs):
    output_path: str | None = kwargs["outputlocation"]
    visualize: bool = kwargs["visualize"]
    run_algos(set(arg), output_path, visualize=visualize)

def run_algos(lang: set[str] | set[tuple[int, ...]], output_path: str | None, visualize: bool =False) -> tuple[int, int, int] | None:
    dfa = DFA()
    dfa.from_lang(lang)
    states_prefixtree = len(dfa.allstates)
    if verbose: print(f"number of states in prefix tree: {states_prefixtree}")
    dfa.revuz()
    l_revuz = dfa.lang()
    states_dfa = len(dfa.allstates)
    if verbose: print(f"number of states in minimal DFA: {states_dfa}")
    dfcaMin = dfcaMinimizer()
    dfcaMin.from_lang(lang)
    dfcaMin.minimize()
    dfca = DFCA()
    dfca.from_minimizer(dfcaMin)
    l_revuz = dfa.lang()
    states_dfca = len(dfca.allstates)
    if verbose: print(f"number of states in minimal DFCA: {states_dfca}")
    l_dfca = frozenset(dfca.decode())
    expected = frozenset(lang_to_int_lang(lang))
    if l_dfca != expected:
        print(f"error: decoding the dfca of language l = {expected} did not result in l, resulted in {l_dfca} (DFCA)")
        dfca.visualize()
        dfcaMin.visualize()
    if l_revuz != expected:
        print(f"error: decoding the dfca of language l = {expected} did not result in l, resulted in {l_revuz} (DFA)")
        dfa.visualize()

    if output_path:
        dfca.to_file(Path(output_path))

    if states_dfca > states_dfa:
        dfa.visualize()
        dfcaMin.visualize()
        dfca.visualize()
        dfca.to_file(Path("suspicious.dfca"))
        input("For the visualized DF(C)As, the minimal DFA is smaller than the corresponding \"minimal\" DFCA..")
    elif visualize:
        dfa.visualize()
        dfcaMin.visualize()
        dfca.visualize()
    return states_prefixtree, states_dfa, states_dfca

verbose = False
def main():
    from argparse import ArgumentParser, BooleanOptionalAction
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
    parser.add_argument("-v", "--visualize", action=BooleanOptionalAction, default=False)
    parser.add_argument("-V", "--verbose", action=BooleanOptionalAction, default=False)
    args = parser.parse_args()
    # TODO this (global variable) is not very elegant but maybe okay..
    global verbose
    verbose = args.verbose

    args.func(**vars(args))

if __name__ == "__main__":
    main()