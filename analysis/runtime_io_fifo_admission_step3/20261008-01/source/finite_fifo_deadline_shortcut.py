"""Simple witness certificates; unresolved sample extrema are NEVER exact bounds.

No novelty claim: unavoidable simultaneous losses, guaranteed timely jobs and
global count bounds. A five-point probe only certifies when both bounds attain.
"""
from fractions import Fraction as F
from itertools import groupby
from finite_fifo_deadline_reference import Problem,replay


def solve_shortcut(problem):
    if not isinstance(problem,Problem):
        raise ValueError('solve_shortcut requires a validated Problem')
    n=len(problem.arrivals)
    if problem.system_slots>=n:
        # Rejection impossible, all fixed-trace completions monotone in common s.
        samples=[problem.service_min,problem.service_max]
        mode='no-rejection monotonic endpoints'
    else:
        samples=sorted({problem.service_min+(problem.service_max-problem.service_min)*F(k,4)
                        for k in range(5)})
        mode='five witnesses with independent global count bounds'
    mandatory=sum(max(0,len(list(group))-problem.system_slots)
                  for _,group in groupby(problem.arrivals))
    guaranteed_timely=0
    if problem.service_max<=problem.relative_deadline:
        guaranteed_timely=1+sum(b-a>=problem.system_slots*problem.service_max
                                for a,b in zip(problem.arrivals,problem.arrivals[1:]))
    lower=n if problem.service_min>problem.relative_deadline else mandatory
    upper=n-guaranteed_timely
    values=[(s,replay(problem,s,include_offers=True)) for s in samples]
    minimum=min(values,key=lambda pair:pair[1]['failures'])
    maximum=max(values,key=lambda pair:pair[1]['failures'])
    exact=mode=='no-rejection monotonic endpoints' or (
        minimum[1]['failures']==lower and maximum[1]['failures']==upper)
    result=dict(method='simple exact-if-certified witness shortcut',status='exact' if exact else 'undetermined',
        mode=mode,problem=problem.to_json(),proved_lower_count=lower,proved_upper_count=upper,
        sampled_minimum_count=minimum[1]['failures'],sampled_maximum_count=maximum[1]['failures'],
        stats=dict(fixed_parameter_replays=len(samples)),novelty_established=False)
    if exact:
        for name,pair in [('minimum',minimum),('maximum',maximum)]:
            s,value=pair
            result[name]=dict(failures=value['failures'],failure_fraction=value['failure_fraction'],
                witness_service_time=str(s),witness_replay=value)
    return result
