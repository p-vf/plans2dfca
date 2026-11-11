from graphviz import Digraph
from typing import cast

# example from the paper revuz.pdf
input_words = {"aa", "aaa", "aaba", "aabbb", "abaa", "ababb", "abbab", "baa", "babb", "abaa", "bbbab", "caaad", "caac", "cbaad", "cbac", "ebb"}

class State:
    def __init__(self, id: int, sentinel: "State | None", final: bool, successors: dict[int, "State"] | None = None):
        if successors is None:
            successors = {}
        self.succ = successors
        self.id = id
        # if sentinel is None, then final has to be false, because this state
        #   (self) is the sentinel state (which can never be final)
        assert not final or sentinel
        self.sentinel = sentinel if sentinel else self
        self.parents: dict["State", set[int]] = {} # TODO this should be a mapping from State to a (set of) character.
        # a height of -1 means the height of this state is undefined.
        self.height = -1

    def add_succ(self, char: int, succ: "State"):
        assert char not in self.succ
        self.succ[char] = succ

    def update_succ(self, char: int, succ: "State"):
        assert char in self.succ
        self.succ[char] = succ

    def add_parent(self, parent: "State", character: int):
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

class DFA:
    def __init__(self):
        self.sentinel = State(-1, None, False)
        self.initial = State(0, self.sentinel, False)
        self.allstates = {self.sentinel, self.initial}
        self.finalstates: set["State"] = set()
        self.alphabet: set[int] = set()

    def from_lang(self, language: set[tuple[int, ...]] | set[str]):
        """generates the prefix-tree of a given language"""
        if isinstance(next(iter(language)), str):
            language = cast(set[str], language)
            old_lang: set[str] = language
            language = set([tuple(map(ord, w)) for w in old_lang])
        language = cast(set[tuple[int, ...]], language)
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
        height = 0
        next_states = set(self.finalstates)
        while next_states:
            curr_states = next_states
            next_states = set()
            while curr_states:
                state = curr_states.pop()
                state.height = max(state.height, height)
                maxheight = max(state.height, maxheight)
                for parent in state.parents:
                    next_states.add(parent)
            height += 1

        partition = [set() for _ in range(maxheight + 1)]
        for s in self.allstates:
            if s.height >= 0:
                partition[s.height].add(s)
        return partition

    def visualize(self):
        dot = Digraph(engine="fdp")
        dot.graph_attr["maxiter"] = "100"
        for state in self.allstates:
            iden = str(state.id)
            dot.node(iden, iden, peripheries="2" if state in self.finalstates else "1")
        for state in self.allstates:
            iden = str(state.id)
            for char in state.succ:
                dot.edge(iden, str(state.succ[char].id), str(char))
        dot.render(view=True)

    def lang(self):
        # NOTE: if there is a cycle in the dfa, this function does not terminate
        stack: list[tuple[State, tuple[int, ...]]] = [(self.initial, ())]
        res: set[tuple[int, ...]] = set()

        while stack:
            state, prefix = stack.pop()
            if state in self.finalstates:
                res.add(prefix)
            for char in state.succ:
                stack.append((state.succ[char], prefix + (char,)))
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
            for char in b.parents[parent]:
                parent.update_succ(char, a)
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
        # we do this with a breadth-first traversal
        state_depth = {}
        depth = 0
        next_states = set([self.initial])
        while next_states:
            curr_states = next_states
            next_states: set[State] = set()
            while curr_states:
                state = curr_states.pop()
                if state in state_depth:
                    continue
                state_depth[state] = depth
                for char in state.succ:
                    next_states.add(state.succ[char])
            depth += 1
        max_depth = depth - 1

        states_by_depth = [set() for _ in range(max_depth + 1)]
        for state in state_depth:
            states_by_depth[state_depth[state]].add(state)

        iter = 0
        for stateset in states_by_depth:
            for state in stateset:
                state.id = iter
                iter += 1
        self.sentinel.id = len(self.allstates) - 1

def group_str(chars: set[int]) -> str:
    num_iter = iter(sorted(chars))
    start = next(num_iter)
    ranges: list[tuple[int, int]]= [(start, start)]
    for i in num_iter:
        if i != ranges[-1][1] + 1:
            ranges.append((i,i))
        else:
            ranges[-1] = (ranges[-1][0], i)
    res = ""
    for i in range(len(ranges)):
        (s, e) = ranges[i]
        if s == e:
            res += str(s)
        elif s == e - 1:
            res += str(s) + "," + str(e)
        else:
            res += str(s) + ".." + str(e)
        res += "," if i < len(ranges) else ""
    return res

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