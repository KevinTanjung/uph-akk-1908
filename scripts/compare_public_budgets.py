"""Compare matched 1000- and 10000-evaluation results and verify their shared search prefix."""
import argparse
import csv
import hashlib
import json
import statistics
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.analyze_public_results import EXPERIMENT,ALPHA,holm,load_blocks,paired_test

CANDIDATE=ROOT/'experiments/public-18-10000'


def check_prefixes(baseline, candidate):
    old_audit=json.loads((baseline/'audit.json').read_text())
    new_audit=json.loads((candidate/'audit.json').read_text())
    old_raw=ROOT/old_audit['raw_output_directory']
    new_raw=ROOT/new_audit['raw_output_directory']
    checked=0
    with (baseline/'runs.csv').open() as stream:
        rows=list(csv.DictReader(stream))
    for row in rows:
        name=row['run_id']+'.json'
        old_content=(old_raw/name).read_bytes();new_content=(new_raw/name).read_bytes()
        if hashlib.sha256(old_content).hexdigest()!=old_audit['raw_sha256'][name] or hashlib.sha256(new_content).hexdigest()!=new_audit['raw_sha256'][name]:
            raise ValueError('raw run changed: '+name)
        old=json.loads(old_content);new=json.loads(new_content)
        if any(old[key]!=new[key] for key in ('instance','algorithm','seed','parameters')):
            raise ValueError('unmatched run: '+name)
        prefix=new['history'][:old['budget']]
        if [(e['current'],e['best']) for e in prefix]!=[(e['current'],e['best']) for e in old['history']]:
            raise ValueError('search prefix differs: '+name)
        if new['makespan']>old['makespan']:
            raise ValueError('best-so-far worsened: '+name)
        checked+=1
    return dict(matched_runs=checked,matched_candidate_evaluations=checked*old_audit['evaluations_per_run'],
                status='Every current and best makespan in every 1000-evaluation prefix matches; elapsed times excluded')


def compare(baseline=EXPERIMENT,candidate=CANDIDATE,tuning=False):
    baseline,candidate=Path(baseline),Path(candidate)
    old_protocol,_,old_rpds=load_blocks(baseline)
    new_protocol,_,new_rpds=load_blocks(candidate)
    keys=('instances','algorithms','seeds','parameters') if tuning else ('instances','algorithms','seeds','parameters','parameter_overrides')
    for key in keys:
        if old_protocol[key]!=new_protocol[key]: raise ValueError('protocol mismatch: '+key)
    if tuning:
        if old_protocol['budget']!=new_protocol['budget']: raise ValueError('tuning comparison requires equal budgets')
    elif old_protocol['budget']>=new_protocol['budget']: raise ValueError('candidate budget must be larger')
    old_stats=json.loads((baseline/'statistics.json').read_text())
    new_stats=json.loads((candidate/'statistics.json').read_text())
    for folder,stats in ((baseline,old_stats),(candidate,new_stats)):
        for name,digest in stats['input_sha256'].items():
            if hashlib.sha256((folder/name).read_bytes()).hexdigest()!=digest:
                raise ValueError('statistics inputs changed: '+str(folder/name))
    algorithms=old_protocol['algorithms']
    rows_by_budget=[]
    for folder in (baseline,candidate):
        with (folder/'runs.csv').open() as stream: rows_by_budget.append(list(csv.DictReader(stream)))
    improvements=[];instance_rows=[]
    for index,algorithm in enumerate(algorithms):
        differences=[new[index]-old[index] for old,new in zip(old_rpds,new_rpds)]
        old_values=[float(row[index]) for row in old_rpds];new_values=[float(row[index]) for row in new_rpds]
        old_mean,new_mean=statistics.mean(old_values),statistics.mean(new_values)
        counts=[]
        for records in rows_by_budget:
            group=[r for r in records if r['algorithm']==algorithm]
            counts.append(sum(float(r['rpd'])==0 for r in group))
        improvements.append(dict(algorithm=algorithm,baseline_mean_rpd=old_mean,candidate_mean_rpd=new_mean,
                                 mean_rpd_reduction_pp=old_mean-new_mean,
                                 median_instance_rpd_reduction_pp=statistics.median([-float(d) for d in differences]),
                                 baseline_optimum_hits=counts[0],candidate_optimum_hits=counts[1],
                                 improved_instances=sum(d<0 for d in differences),tied_instances=sum(d==0 for d in differences),
                                 worse_instances=sum(d>0 for d in differences),**paired_test(differences)))
        for name,old,new in zip(old_protocol['instances'],old_values,new_values):
            instance_rows.append(dict(instance=name,algorithm=algorithm,baseline_mean_rpd=old,candidate_mean_rpd=new,reduction_pp=old-new))
    for row,pvalue in zip(improvements,holm([row['pvalue'] for row in improvements])):
        row['holm_pvalue']=pvalue;row['significant_at_0_05']=pvalue<ALPHA
    pairs=[]
    for old,new in zip(old_stats['posthoc'],new_stats['posthoc']):
        if (old['algorithm_a'],old['algorithm_b'])!=(new['algorithm_a'],new['algorithm_b']):
            raise ValueError('post-hoc pair ordering differs')
        pairs.append(dict(algorithm_a=old['algorithm_a'],algorithm_b=old['algorithm_b'],
                          baseline_holm_pvalue=old['holm_pvalue'],candidate_holm_pvalue=new['holm_pvalue'],
                          baseline_significant=old['significant_at_0_05'],candidate_significant=new['significant_at_0_05'],
                          baseline_median_gap_pp=old['median_rpd_difference_a_minus_b_pp'],
                          candidate_median_gap_pp=new['median_rpd_difference_a_minus_b_pp']))
    result=dict(baseline_budget=old_protocol['budget'],candidate_budget=new_protocol['budget'],
                unit='18 paired instance means, each over the same 20 seeds',alpha=ALPHA,
                within_budget_family='Six algorithm pairs per setting, Holm correction separately at each setting' if tuning else 'Six algorithm pairs per budget, Holm correction separately at each budget',
                budget_change_family='Four two-sided exact Wilcoxon tests of tuning changes, Holm correction across algorithms' if tuning else 'Four two-sided exact Wilcoxon tests of mean RPD change, Holm correction across algorithms',
                caveats=['Parameters were selected only on the disjoint pilots; improvements on final benchmarks are not guaranteed',
                         'Matching seed numbers do not imply matching search paths when parameters change',
                         'Both campaigns used four concurrent processes; runtime includes I/O and contention'] if tuning else ['Budgets share the same search prefixes, so best-so-far non-worsening is guaranteed by construction',
                         'Significance at one budget but not another does not itself prove a change in the algorithm gap',
                         'The 10000-evaluation campaign used four concurrent processes and cached fixed inputs; runtimes are not isolated speed comparisons'],
                prefix_verification=dict(status='Not applicable: changed parameters need not share search prefixes') if tuning else check_prefixes(baseline,candidate),improvements=improvements,posthoc_comparison=pairs,
                baseline_friedman=old_stats['friedman'],candidate_friedman=new_stats['friedman'],
                input_sha256={str(folder.relative_to(ROOT))+'/'+name:hashlib.sha256((folder/name).read_bytes()).hexdigest()
                              for folder in (baseline,candidate) for name in ('protocol.json','runs.csv','statistics.json','audit.json')})
    stem='tuning-comparison' if tuning else 'budget-comparison'
    (candidate/(stem+'.json')).write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    with (candidate/(stem+'.csv')).open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(instance_rows[0]));writer.writeheader();writer.writerows(instance_rows)
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline',type=Path,default=EXPERIMENT)
    parser.add_argument('--candidate',type=Path,default=CANDIDATE)
    parser.add_argument('--tuning',action='store_true')
    args=parser.parse_args();compare(args.baseline,args.candidate,args.tuning)
