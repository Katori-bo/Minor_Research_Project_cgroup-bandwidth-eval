"""Independent tiny-trace checker using reachable symbolic decision branches.

Imports only the input type/number parser, never the reference replay or global
breakpoint generator. This is not an SMT baseline or an originality claim.
"""
from dataclasses import dataclass
from fractions import Fraction
from finite_fifo_deadline_reference import Problem, BudgetExceeded


@dataclass(frozen=True)
class Domain:
    low: Fraction
    high: Fraction
    left_closed: bool = True
    right_closed: bool = True

    def valid(self):
        return self.low < self.high or (self.low == self.high and self.left_closed and self.right_closed)

    def contains(self, s):
        return ((s > self.low or (s == self.low and self.left_closed)) and
                (s < self.high or (s == self.high and self.right_closed)))

    def split_le(self, cut):
        if cut < self.low:
            return None, self
        if cut >= self.high:
            return self, None
        yes = Domain(self.low,cut,self.left_closed,True)
        no = Domain(cut,self.high,False,self.right_closed)
        return (yes if yes.valid() else None), (no if no.valid() else None)

    def to_json(self):
        return dict(low=str(self.low),high=str(self.high),
                    left_closed=self.left_closed,right_closed=self.right_closed)


@dataclass(frozen=True)
class State:
    domain: Domain
    pending: tuple = ()  # Affine completion pairs (intercept, positive slope).
    rejected: int = 0
    late: int = 0


def symbolic_solve(problem, max_states=5000, max_transitions=100000):
    if not isinstance(problem, Problem):
        raise ValueError('symbolic_solve requires a validated Problem')
    if any(type(x) is not int or x < 1 for x in (max_states,max_transitions)):
        raise ValueError('positive integer symbolic limits required')
    states = [State(Domain(problem.service_min,problem.service_max))]
    transitions = splits = 0
    peak_states = 1
    for arrival in problem.arrivals:
        todo = list(states)
        ready = []
        # Remove completed requests symbolically; retained completions are > arrival.
        while todo:
            state = todo.pop()
            transitions += 1
            if transitions > max_transitions:
                raise BudgetExceeded('symbolic transition budget exceeded')
            if not state.pending:
                ready.append(state)
            else:
                intercept,slope = state.pending[0]
                yes,no = state.domain.split_le((arrival-intercept)/slope)
                splits += yes is not None and no is not None
                if yes is not None:
                    todo.append(State(yes,state.pending[1:],state.rejected,state.late))
                if no is not None:
                    ready.append(State(no,state.pending,state.rejected,state.late))
            peak_states = max(peak_states,len(todo)+len(ready))
            if peak_states > max_states:
                raise BudgetExceeded('symbolic state budget exceeded')
        states = []
        for state in ready:
            transitions += 1
            if transitions > max_transitions:
                raise BudgetExceeded('symbolic transition budget exceeded')
            if len(state.pending) == problem.system_slots:
                states.append(State(state.domain,state.pending,state.rejected+1,state.late))
            else:
                if state.pending:
                    b,m = state.pending[-1]
                    completion = (b,m+1)
                else:
                    completion = (arrival,1)
                b,m = completion
                timely,late = state.domain.split_le((arrival+problem.relative_deadline-b)/m)
                splits += timely is not None and late is not None
                pending = state.pending+(completion,)
                if timely is not None:
                    states.append(State(timely,pending,state.rejected,state.late))
                if late is not None:
                    states.append(State(late,pending,state.rejected,state.late+1))
            peak_states = max(peak_states,len(states))
            if peak_states > max_states:
                raise BudgetExceeded('symbolic state budget exceeded')
    states.sort(key=lambda state:(state.domain.low,not state.domain.left_closed,state.domain.high))
    n = len(problem.arrivals)
    cells = [dict(domain=state.domain.to_json(),rejected=state.rejected,late=state.late,
                  failures=state.rejected+state.late,
                  failure_fraction=str(Fraction(state.rejected+state.late,n))) for state in states]
    return dict(method='independent reachable symbolic branches; tiny-check baseline',cells=cells,
                minimum_failures=min(c['failures'] for c in cells),
                maximum_failures=max(c['failures'] for c in cells),
                stats=dict(transitions=transitions,splits=splits,peak_states=peak_states))
