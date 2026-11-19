#!/usr/bin/env python3
"""Q2-F canonical manuscript integration, only after verified Q2 scientific gate.

Run in the original T3 checkout with a *separate* authorized checkout of
ALRIER/Genetic_Algorithms as --paper. Does not create any second manuscript.
Never changes Q1 numeric results, source experiment or Stage12 calibration.
"""
import argparse,csv,hashlib,json,math,re,shutil
from pathlib import Path

def check(condition,why):
    if not condition:raise RuntimeError("Q2 manuscript integration gate: "+why)

def latex(s):
    return str(s).replace("_",r"\_").replace("%",r"\%").replace("&",r"\&")

def read_csv(path):
    with path.open(newline="") as f:return list(csv.DictReader(f))

def fmt(x):
    return f"{float(x):+.2f}"

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,required=True)
    p.add_argument("--paper",type=Path,required=True)
    p.add_argument("--report",type=Path,required=True)
    a=p.parse_args()
    q=a.root/"synthesis"
    gate=json.loads((q/"Q2_SCIENTIFIC_AUDIT.json").read_text())
    check(gate["status"]=="PASS_Q2_A_TO_E_REUSE_ORIGINAL" and
          gate["all_18_blocks_verified"] and gate["recovered_original_archives"]==180,
          "cannot integrate unverified or incomplete Q2")
    inventory=json.loads((q/"Q2_SYNTHESIS_SHA256_MANIFEST.json").read_text())
    for name,item in inventory.items():
        f=q/name
        check(f.is_file() and hashlib.sha256(f.read_bytes()).hexdigest()==item["sha256"],
              "Q2 synthesis file SHA mismatch "+name)
    by_n=read_csv(q/"Q2_TABLE_FAMILY_BY_SAMPLE_SIZE_DE_OWN.csv")
    by_m=read_csv(q/"Q2_TABLE_FAMILY_BY_MECHANISM_DE_OWN.csv")
    primary=read_csv(q/"Q2_PRIMARY_DE_216_EXPLORATORY_CONTRASTS.csv")
    sensitivity=read_csv(q/"Q2_TABLE_FOUR_METHOD_BENCHMARK_SENSITIVITY.csv")
    check(len(by_n)==18 and len(by_m)==36 and len(primary)==216 and len(sensitivity)==8,
          "Q2 results denominators and main display source rows")
    own=next(x for x in sensitivity if x["method"]=="de" and x["benchmark_role"]=="own")
    mean=next(x for x in sensitivity if x["method"]=="de" and x["benchmark_role"]=="mean")
    positive=int(own["joint_positive"]);opportunities=int(own["observations"])
    check(opportunities==18*240 and 0<=positive<=opportunities,"DE Q2 denominator")
    fam=("normal","lognormal","weibull","invgauss","exgaussian","exwald")
    names={"normal":"Normal","lognormal":"Lognormal","weibull":"Weibull",
           "invgauss":"Inverse Gaussian","exgaussian":"Ex Gaussian","exwald":"Ex Wald"}
    rows=[]
    for f in fam:
        for n in (200,1000,3000):
            hits=[x for x in by_n if x["family"]==f and int(x["sample_n"])==n]
            check(len(hits)==1,"missing family/sample profile")
            x=hits[0]
            rows.append(f"{latex(names[f])} & {n:,} & {fmt(x['mean_mse_gain_pct'])} & "+
                        f"{fmt(x['mean_q95_gain_pct'])} & "+
                        f"{int(x['joint_positive'])}/{int(x['eligible_scenarios'])} \\\\")
    table=r"""
\begin{table}[htbp]
\centering\scriptsize
\caption{Independent within-family Held Out effects of the originally frozen DE
composites compared with the classical reference selected in Discovery.
Each family-size row averages the 240 contaminated support scenarios
(six mechanisms times 40 selected settings). Positive percentage gains
favor DE; joint positive counts require favorable mean effects for BOTH MSE
and $Q_{.95}$. Counts are descriptive, not calibrated significance claims.}
\label{tab:q2_family_size}
\begin{tabular}{@{}lrrrr@{}}
\toprule
Evaluation family & $n$ & MSE gain (\%) & $Q_{.95}$ gain (\%) & Joint positive\\
\midrule
"""+"\n".join(rows)+r"""
\bottomrule
\end{tabular}
\end{table}
"""
    mechanism_values=sorted(by_m,key=lambda x:float(x["avg_mse_gain_pct"]),reverse=True)
    biggest=mechanism_values[0];worst=mechanism_values[-1]
    q2=r"""
\subsection{Statistical Regimes and Composite Estimator Performance}\label{sec:q2_results}

Q1 established that differential evolution was the strongest tested search
procedure on the two-objective frontier. Q2 asks under which original
distribution, sample-size and contamination conditions its independently
evaluated \emph{frozen} composites improve estimation relative to a
competitive classical reference. We analyze within-family training and
evaluation only; cross-family transfer and previously unseen mechanisms
are addressed separately in Q3. The original 241 supported scenarios contain
one clean reference and 40 observed settings for each of six contamination
mechanisms. Their contamination fractions and MAD-scaled severities were
selected before the results were observed.

Across 18 evaluation family-size blocks and 240 contaminated settings per
block, DE achieves average positive gains in both MSE and $Q_{.95}$ in
""" + f"{positive:,} of {opportunities:,} ({100*positive/opportunities:.1f}\\%)" + r"""
scenario-level summaries when measured against the original frozen
classical comparator. Both positive and unfavorable outcomes remain
included in the denominator. These summaries are computed from matched
original training and independent evaluation seeds, and describe
\emph{the observed supported scenario grid}. They do not establish a
general-purpose rule for selecting estimators in unobserved regimes.

Percentage reductions are computed relative to the independent frozen
classical reference. When reference loss is small, an unfavorable ratio can
become large in magnitude; reported mean percentages should therefore be
read together with the signs, eligible counts, original loss differences and
robustness diagnostics in the appendix. The benchmark is deliberately
competitive, and DE's Q1 optimizer ranking does not imply positive gains
over that reference in every supported scenario.

Table~\ref{tab:q2_family_size} separates the six generating families and
three sample sizes. Figure~\ref{fig:q2_family_mechanism} further distinguishes
six contamination mechanisms for both loss outcomes. The most favorable
observed family-mechanism average for MSE is """ + \
        latex(names[biggest["family"]])+ " with "+latex(biggest["mechanism"].replace("_"," "))+ \
        f" ({fmt(biggest['avg_mse_gain_pct'])}\\%),"+r"""
while the least favorable is """+latex(names[worst["family"]])+" with "+ \
        latex(worst["mechanism"].replace("_"," "))+ \
        f" ({fmt(worst['avg_mse_gain_pct'])}\\%)."+r"""
The comparisons are associations under the originally sampled regimes;
we do not infer how a mechanism would behave under a different untested
fraction-severity combination.

"""+table+r"""
\begin{figure}[htbp]
\centering
\includegraphics[width=\linewidth]{figures/results_q2_DE_family_mechanism.png}
\caption{Descriptive percentage changes in independently evaluated
within-family DE performance relative to the original frozen classical
benchmark, averaged over three sample sizes and 40 selected scenarios per
mechanism. Positive means lower loss for DE; negative means the classical
reference has lower loss. The panels display MSE and $Q_{.95}$
separately and include unfavorable regimes.}
\label{fig:q2_family_mechanism}
\end{figure}

Fraction and severity must be interpreted jointly with the mechanism.
Only 40 of 63 possible fraction-severity combinations were selected for
each mechanism. We therefore report observed local-neighbor contrasts,
holding one design dimension fixed, rather than extrapolating a complete
factorial surface. The corresponding observed-cell heatmap and full
factor tables are in Appendix~\ref{app:q2_detail}. Changing the benchmark
from the frozen classical comparator to the sample mean also changes
the estimated gains; on the non-clean supported cells, DE's average
gains relative to the two references are """ + \
        fmt(own["mean_mse_gain_pct"])+r"""\% and """+fmt(mean["mean_mse_gain_pct"])+r"""\%
for MSE, respectively. That difference is part of Q4's benchmark
sensitivity, and does not alter the original Q2 reference policy.

For uncertainty, a two-way bootstrap resamples the ten training and
ten independent evaluation seeds separately, while retaining the
original fixed set of scenario identities. Results are conditional on
these fitted candidates and on the observed design. The 216 primary DE
mechanism-by-block-by-metric comparisons and their post hoc BH-adjusted
values are \emph{exploratory}: the calibration performed for Q1's different
216 optimizer-pair contrasts does not validate a nominal 5\% error rate
for Q2. The appendix records these restrictions, the original provenance
and the full favorable and unfavorable profiles.

\FloatBarrier
"""
    appendix=r"""
\section{Q2 Regime Profiles and Sensitivity Analysis}\label{app:q2_detail}
This appendix documents the Q2 within-family, original frozen-candidate
analysis. Each supported contaminated mechanism has 40 prespecified
fraction-severity settings, not the complete 63-cell factorial grid.
The original evaluation uses ten training seeds crossed with ten
disjoint Held Out evaluation seeds. Original scenario identity is fixed
during two-way seed resampling; no original optimizer selection or
Monte Carlo production was rerun. The full 18-block cross-seed score
tables, the 216 original primary DE conditional contrast inventory,
factor profiles, observed local-neighbor comparisons, adverse outcomes,
all source checksums and scientific audit are permanently retained in
\texttt{T3/Q2/}.

The two-way bootstrap uses 2,048 independent resampling draws per
method, benchmark, mechanism, distribution and sample-size block, resampling
training and evaluation seed axes separately. The resulting intervals
represent uncertainty in those two seed dimensions conditional on the
observed scenario design. They do not guarantee selection-aware coverage
or familywise error control. The 216-comparison post hoc BH analysis
is an exploratory multiple-testing diagnostic; no inference from Q1
Stage 12's different synthetic surrogate is transferred to Q2.

\begin{figure}[htbp]
\centering
\includegraphics[width=.98\linewidth]{figures/results_q2_DE_fraction_severity.png}
\caption{Observed contamination fraction and MAD-scaled severity cells.
Each label gives the average of DE's percentage MSE and $Q_{.95}$
gains relative to the frozen classical benchmark and the number of
original source-scenario combinations contributing to that cell.
Unobserved cells are not interpolated or assigned fabricated results.
This descriptive display averages across source families, sample sizes
and the six supported contamination mechanisms.}
\label{fig:q2_fraction_severity}
\end{figure}

The primary text reports family and size effects. Detailed mechanism
effects, all four search engines under both classical reference policies,
paired local-neighbor evidence, crossed-seed uncertainty and source
manifest information are available as companion CSV and JSON files. The
choice of DE as the principal Q2 search was informed by Q1 on related
data; inferential claims about newly discovered regime boundaries require
independent confirmation before deployment.

\FloatBarrier
"""
    paper=a.paper
    tex=paper/"manuscript/main.tex"
    check(tex.is_file(),"canonical private repository manuscript not checked out")
    original=tex.read_text()
    st=r"\subsection{Statistical Regimes Associated with Improved Estimation}"
    end=r"\FloatBarrier"+"\n"+r"\subsection{Generalization Beyond the Training Conditions}"
    check(original.count(st)==1 and original.count(end)==1,"Q2 original Results anchors changed")
    i=original.index(st)
    j=original.index(end,i)
    # Original cross-family marginal counts are preserved in Q2 source archive.
    updated=original[:i]+q2+"\n"+original[j:]
    appendAnchor=r"\section{Experimental Accounting and Candidate Diagnostics}\label{app:experimental_accounting}"
    check(updated.count(appendAnchor)==1,"expected one canonical appendix anchor")
    updated=updated.replace(appendAnchor,appendix+"\n"+appendAnchor)
    methAnchor=r"\subsection{Reproducibility and Computational Implementation}"
    check(updated.count(methAnchor)==1,"expected one Methods endpoint")
    short=r"""The Q2 regime analysis compares unchanged frozen composites with
their Discovery-selected classical references on supported independent
Held Out scenarios, grouped by generating family, sample size,
contamination mechanism, fraction and MAD-scaled severity. Matched
training/evaluation-seed sensitivity, observed-cell neighbor comparisons
and the limitations of post hoc testing are detailed in
Appendix~\ref{app:q2_detail}.

"""
    updated=updated.replace(methAnchor,short+methAnchor)
    labels=re.findall(r"\\label\{([^}]+)\}",updated)
    refs=re.findall(r"\\(?:ref|eqref|pageref|autoref)\{([^}]+)\}",updated)
    check(len(labels)==len(set(labels)),"duplicate LaTex labels after Q2 integration")
    check(not set(refs).difference(labels),"unresolved LaTex reference after Q2 integration: "+str(set(refs)-set(labels)))
    check(updated.count(r"\section{Results}") == 1 and
          updated.count(r"\section{Methods}") == 1 and
          updated.count(r"\subsection{Statistical Regimes and Composite Estimator Performance}") == 1,
          "single canonical manuscript sections")
    figs=paper/"manuscript/figures"
    figs.mkdir(parents=True,exist_ok=True)
    copied=[]
    for a_name,b_name in (
        ("figure_Q2_DE_family_mechanism","results_q2_DE_family_mechanism"),
        ("figure_Q2_DE_fraction_severity","results_q2_DE_fraction_severity")
    ):
        for ext in ("png","svg"):
            source=q/(a_name+"."+ext)
            dest=figs/(b_name+"."+ext)
            check(source.is_file() and source.stat().st_size>1000,"figure source absent")
            shutil.copy2(source,dest)
            copied.append(str(dest))
    # Retain original scientific files; a plot removed from Results is deleted
    # only if no longer referenced anywhere in the canonical manuscript.
    old=(figs/"results_heldout_family_leaders.png",
         figs/"results_heldout_family_leaders.svg")
    if "results_heldout_family_leaders.png" not in updated:
        for stale in old:
            if stale.exists():stale.unlink()
    tex.write_text(updated)
    result=dict(status="Q2_F_CANONICAL_TEX_UPDATED",paper_path=str(tex),
                manuscript_old_sha256=hashlib.sha256(original.encode()).hexdigest(),
                manuscript_new_sha256=hashlib.sha256(updated.encode()).hexdigest(),
                q2_primary_positive=positive,q2_primary_eligible=opportunities,
                unique_latex_labels=len(labels),all_crossrefs_resolved=True,
                publication_figures=copied,external_experiment_rerun=False,
                stage12_q1_results_altered=False,
                compilation="Automatically triggered by canonical manuscript GitHub workflow after push")
    a.report.parent.mkdir(parents=True,exist_ok=True)
    a.report.write_text(json.dumps(result,indent=2)+"\n")
    print("Q2_F_CANONICAL_MANUSCRIPT_SOURCE_INTEGRATION_PASS",str(tex),flush=True)
if __name__=="__main__":main()
