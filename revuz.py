from graphviz import Digraph

# example from the paper revuz.pdf
input_words = {"aa", "aaa", "aaba", "aabbb", "abaa", "ababb", "abbab", "baa", "babb", "abaa", "bbbab", "caaad", "caac", "cbaad", "cbac", "ebb"}

class State:
    def __init__(self, id: int, sentinel: "State | None", final: bool, successors: dict[str, "State"] | None = None):
        if successors is None:
            successors = {}
        for char in successors:
            assert len(char) == 1
        self.succ = successors
        self.id = id
        # if sentinel is None, then final has to be false, because this state
        #   (self) is the sentinel state (which can never be final)
        assert not final or sentinel
        self.sentinel = sentinel if sentinel else self
        self.parents: dict["State", str] = {} # TODO this should be a mapping from State to a (set of) character.
        # a height of -1 means the height of this state is undefined.
        self.height = -1

    def add_succ(self, char: str, succ: "State"):
        assert char not in self.succ
        assert len(char) == 1
        self.succ[char] = succ

    def update_succ(self, char: str, succ: "State"):
        assert char in self.succ
        assert len(char) == 1
        self.succ[char] = succ

    def add_parent(self, parent: "State", character: str):
        self.parents[parent] = character

    def set_height(self, height: int):
        self.height = max(self.height, height)

    def next(self, char: str):
        assert len(char) == 1
        return self.succ.get(char, self.sentinel)

    def __repr__(self):
        return "State(" + str(self.id) + ")"

class DFA:
    def __init__(self):
        self.sentinel = State(-1, None, False)
        self.initial = State(0, self.sentinel, False)
        self.allstates = {self.sentinel, self.initial}
        self.finalstates: set["State"] = set()
        self.alphabet: set[str] = set()

    def from_lang(self, language: set[str]):
        """generates the prefix-tree of a given language"""
        for w in language:
            curr = self.initial
            for i in range(len(w)):
                assert curr != self.sentinel
                if w[i] not in self.alphabet:
                    self.alphabet.add(w[i])
                if curr.next(w[i]) == self.sentinel:
                    newstate = State(len(self.allstates) - 1, self.sentinel, False)
                    self.allstates.add(newstate)
                    curr.add_succ(w[i], newstate)
                    newstate.add_parent(curr, w[i])
                else:
                    # nothing has to be done here, because there already
                    # exists such a state
                    pass
                curr = curr.next(w[i])
                assert len(self.sentinel.succ) == 0
            assert curr != self.sentinel
            self.finalstates.add(curr)
        if not language:
            self.allstates.remove(self.initial)
            self.initial = self.sentinel
        self.sentinel.id = len(self.allstates) - 1

    def get_partition(self):
        # NOTE: this function does not terminate if there is a cycle in the dfa
        # TODO: make this work without the extra ".height" member in State
        #   (adding the state to the correct partition instead of setting a
        #   member variable)
        maxheight = -1
        def traverse_height(state: "State", height: int):
            nonlocal maxheight
            state.set_height(height)
            maxheight = max(height, maxheight)
            for p in state.parents:
                traverse_height(p, height + 1)
        for s in self.finalstates:
            traverse_height(s, 0)
        partition = [set() for _ in range(maxheight + 1)]
        for s in self.allstates:
            if s.height >= 0:
                partition[s.height].add(s)
        return partition

    def visualize(self):
        dot = Digraph()
        for state in self.allstates:
            iden = str(state.id)
            dot.node(iden, iden, peripheries="2" if state in self.finalstates else "1")
        for state in self.allstates:
            iden = str(state.id)
            for char in state.succ:
                dot.edge(iden, str(state.succ[char].id), char)
        dot.render(view=True)

    def lang(self, initial: State | None = None, prefix: str = "") -> set[str]:
        # NOTE: if there is a cycle in the dfa, this function does not terminate
        if initial is None:
            initial = self.initial
        res: set[str] = set()
        if initial in self.finalstates:
            res.add(prefix)
        for char in initial.succ:
            s = self.lang(initial.succ[char], prefix + char)
            res.update(s)
        return res

    def sort_states(self, states: list[State]):
        state_to_num = {state: i for i, state in enumerate(self.allstates)}
        finalstates = self.finalstates
        def to_signature(state: State):
            nonlocal finalstates
            nonlocal state_to_num
            return (state in finalstates, [(character, state_to_num[state.succ[character]]) for character in sorted(state.succ)])
        statetuplelist = [to_signature(state) for state in states]
        sorted_states_tuples = sorted(zip(statetuplelist, states), key = lambda t: t[0])
        sorted_states = [state for _, state in sorted_states_tuples]
        return sorted_states_tuples

    def merge(self, a: State, b: State):
        """merges state b into state a"""
        for k in b.succ:
            succ = b.succ[k]
            succ.add_parent(a, k)
        for parent in b.parents:
            parent.update_succ(b.parents[parent], a)
        self.finalstates.discard(b)
        self.allstates.remove(b)

    def revuz(self):
        p = self.get_partition()
        for h, block in enumerate(map(list, p)):
            if h == 0:
                s = block[0]
                for other in block[1:]:
                    self.merge(s, other)
            else:
                sorted_states_sign = self.sort_states(block)
                prev_sign, prev_state = sorted_states_sign[0]
                for n in sorted_states_sign[1:]:
                    if prev_sign == n[0]:
                        self.merge(prev_state, n[1])
                    else:
                        prev_sign, prev_state = n
        # cleanup: we must order the labels of the states by minimal depth
        state_depth = {}
        max_depth = 0
        def traverse(start: State, depth: int):
            nonlocal self, state_depth, max_depth
            if start in state_depth:
                return
            state_depth[start] = depth
            max_depth = max(max_depth, depth)
            for state in start.succ.values():
                traverse(state, depth + 1)
        traverse(self.initial, 0)

        states_by_depth = [set() for _ in range(max_depth + 1)]
        for state in state_depth:
            states_by_depth[state_depth[state]].add(state)

        iter = 0
        for stateset in states_by_depth:
            for state in stateset:
                state.id = iter
                iter += 1
        self.sentinel.id = len(self.allstates) - 1

def main():
    dfa = DFA()
    print(f"input words: {input_words}")
    dfa.from_lang(input_words)
    dfa.visualize()
    dfa.revuz()
    dfa.visualize()
    P = dfa.get_partition()
    dfa.sort_states(list(dfa.allstates))
    for i, p in enumerate(P):
        print(f"p_{i} = {p}")
    if frozenset(dfa.lang()) == frozenset(input_words):
        print("Generated DFA accepts the same set of words as was input :)")
    else:
        print("Generated DFA does not accept the same set of words as was input :(")

    import random
    error = False
    alphabet = ["a", "b", "c", "d"]
    num_states_prev = 0
    num_states_after = 0
    for i in range(200):
        language = set()
        for _ in range(i):
            word = ""
            for _ in range(random.randint(0, 20)):
                word += alphabet[random.randint(0, len(alphabet)-1)]
            language.add(word)
        d = DFA()
        d.from_lang(language)
        num_states_prev += len(d.allstates)
        prev_result = frozenset(d.lang())
        d.revuz()
        num_states_after += len(d.allstates)
        after_result = frozenset(d.lang())
        if not(after_result == frozenset(language) == prev_result):
            print(f"randomly generated language {language} does not result in the same language..")
            error = True
    if error:
        print("There is a mistake in the implementation :(")
    else:
        print("No mistake in implementation detected :)")
    print(f"States...\n...before revuz: {num_states_prev}\n...after revuz: {num_states_after}")


if __name__ == "__main__":
    main()