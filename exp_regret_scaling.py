#!/usr/bin/env python3
"""Regret scaling experiment: measure Bayesian regret vs T and vs Delta.

Validates the theoretical prediction:
  BayeRegret_LLM(T) <= C1 * sqrt(T * (log|Z| - I_LLM)) + C2 * D_KL * log T

Key measurements:
1. Regret vs T: fit sqrt(T) scaling for LLM-TS vs Uniform-TS
2. Regret vs Delta: verify inverse relationship with noise gap
3. Compare LLM vs Uniform regret ratio vs predicted sqrt(1 - I_LLM/log|Z|)
"""
import numpy as np
import json, os, time, requests
from collections import defaultdict

GATEWAY = 'http://172.16.4.201:8000'
N_ACTIONS = 10
LABELS = [chr(65+i) for i in range(N_ACTIONS)]

# Cache LLM priors for attack states
print('Caching LLM priors for regret experiment...')
LLM_PRIORS = {}
for i in range(3):
    desc = [
        f'Attack step {i+1}: target system with {N_ACTIONS} possible exploits. '
        f'One exploit is optimal (higher success rate), others are decoys. '
        f'Choose the most promising exploit based on available information.',
        f'Step {i+1}: after reconnaissance, several attack vectors identified. '
        f'Select the best exploitation technique from {N_ACTIONS} options.',
        f'Step {i+1}: post-exploitation phase. {N_ACTIONS} possible actions '
        f'for privilege escalation and lateral movement.'
    ][i]
    actions = [
        'Exploit known CVE with Metasploit',
        'SQL injection on login form',
        'SSH brute force with common creds',
        'Buffer overflow on network service',
        'File upload bypass to web shell',
        'Local privilege escalation via SUID',
        'Password hash extraction and crack',
        'ARP spoofing for MITM attack',
        'DNS tunneling for data exfiltration',
        'Reverse shell via command injection'
    ]
    resp = requests.post(f'{GATEWAY}/v1/prior', json={
        'state_description': desc,
        'available_actions': actions
    }, timeout=30)
    raw = resp.json()['probabilities']
    prior = {l: max(raw.get(l, 0.1), 0.01) for l in LABELS}
    total = sum(prior.values())
    LLM_PRIORS[i] = {k: v/total for k, v in prior.items()}
    p_opt = LLM_PRIORS[i].get('A', 0)
    rank = sorted(LLM_PRIORS[i], key=LLM_PRIORS[i].get, reverse=True).index('A') + 1
    print(f'  State {i+1}: P(opt)={p_opt:.3f} rank={rank}/{N_ACTIONS}')
    time.sleep(0.2)

UNI_PRIOR = {l: 1.0/N_ACTIONS for l in LABELS}

# True optimal path cost (known in synthetic experiment)
TRUE_OPT_COST = 3.0  # 3 steps, cost 1 each


def ts_mcts_step(prior, T, pg, pb, R=3, lam=0.05):
    """Single step TS-MCTS. Returns (success, total_cost, n_samples)."""
    alpha = {a: 1.0 for a in LABELS}
    beta = {a: 1.0 for a in LABELS}
    n_samples = 0

    for retry in range(R):
        for t in range(T):
            n_samples += 1
            samples = {}
            for a in LABELS:
                samples[a] = np.random.beta(alpha[a], beta[a]) + lam * prior.get(a, 1.0/N_ACTIONS)
            chosen = max(samples, key=samples.get)
            # Noisy outcome
            reward = np.random.random() < (pg if chosen == 'A' else pb)
            if reward:
                alpha[chosen] += 1.0
            else:
                beta[chosen] += 1.0

        # Select best by posterior mean
        best = max(LABELS, key=lambda a: alpha[a] / (alpha[a] + beta[a]))
        if best == 'A':
            return True, 1.0, n_samples
        # Penalize wrong choice
        beta[best] += 2.0

    return False, 1.0, n_samples


def compute_regret(success, cost, opt_cost=TRUE_OPT_COST/3):
    """Per-step regret: expected cost - optimal cost."""
    return cost - opt_cost if not success else 0.0


def run_regret_experiment(prior, T, pg, pb, n_trials=300, R=3):
    """Run trials and compute average regret."""
    regrets = []
    successes = []
    samples_used = []

    for _ in range(n_trials):
        ok, cost, ns = ts_mcts_step(prior, T, pg, pb, R)
        successes.append(ok)
        regrets.append(compute_regret(ok, cost))
        samples_used.append(ns)

    avg_regret = np.mean(regrets)
    se_regret = np.std(regrets) / np.sqrt(n_trials)
    success_rate = np.mean(successes)
    avg_samples = np.mean(samples_used)

    return {
        'avg_regret': avg_regret,
        'se_regret': se_regret,
        'success_rate': success_rate,
        'avg_samples': avg_samples,
        'n_trials': n_trials
    }


def main():
    sep = '=' * 70
    print(sep)
    print('REGRET SCALING EXPERIMENT')
    print('Validating BayeRegret <= C*sqrt(T*(log|Z| - I_LLM))')
    print(sep)

    # Experiment 1: Regret vs T
    T_vals = [3, 5, 10, 20, 30, 50, 100, 200]
    pg, pb = 0.50, 0.28  # Delta = 0.22
    n_trials = 300

    print(f'\n--- Experiment 1: Regret vs T (Delta={pg-pb:.2f}, n={n_trials}) ---')

    results_T = {'T': T_vals, 'llm_regret': [], 'uni_regret': [], 'llm_se': [], 'uni_se': [],
                 'llm_success': [], 'uni_success': []}

    for T in T_vals:
        r_llm = run_regret_experiment(LLM_PRIORS[0], T, pg, pb, n_trials)
        r_uni = run_regret_experiment(UNI_PRIOR, T, pg, pb, n_trials)
        results_T['llm_regret'].append(r_llm['avg_regret'])
        results_T['uni_regret'].append(r_uni['avg_regret'])
        results_T['llm_se'].append(r_llm['se_regret'])
        results_T['uni_se'].append(r_uni['se_regret'])
        results_T['llm_success'].append(r_llm['success_rate'])
        results_T['uni_success'].append(r_uni['success_rate'])
        print(f'  T={T:4d}: LLM regret={r_llm["avg_regret"]:.4f}±{r_llm["se_regret"]:.4f} '
              f'| Uni regret={r_uni["avg_regret"]:.4f}±{r_uni["se_regret"]:.4f} '
              f'| LLM succ={r_llm["success_rate"]:.2f} Uni succ={r_uni["success_rate"]:.2f}')

    # Fit sqrt(T) scaling: regret = a * sqrt(T) + b
    sqrt_T = np.sqrt(T_vals)
    llm_fit = np.polyfit(sqrt_T, results_T['llm_regret'], 1)
    uni_fit = np.polyfit(sqrt_T, results_T['uni_regret'], 1)
    print(f'\n  LLM regret fit: regret = {llm_fit[0]:.4f}*sqrt(T) + {llm_fit[1]:.4f}')
    print(f'  Uni regret fit: regret = {uni_fit[0]:.4f}*sqrt(T) + {uni_fit[1]:.4f}')
    print(f'  LLM/Uni slope ratio: {llm_fit[0]/uni_fit[0]:.3f}')

    # Experiment 2: Regret vs Delta
    print(f'\n--- Experiment 2: Regret vs Delta (T=30, n={n_trials}) ---')
    T_fixed = 30
    Delta_vals = [0.04, 0.10, 0.15, 0.22, 0.32, 0.42]
    pg_vals = [0.50 + d/2 for d in Delta_vals]  # center around 0.50
    pb_vals = [0.50 - d/2 for d in Delta_vals]

    results_D = {'Delta': Delta_vals, 'llm_regret': [], 'uni_regret': [], 'llm_se': [], 'uni_se': []}

    for pg, pb, d in zip(pg_vals, pb_vals, Delta_vals):
        r_llm = run_regret_experiment(LLM_PRIORS[0], T_fixed, pg, pb, n_trials)
        r_uni = run_regret_experiment(UNI_PRIOR, T_fixed, pg, pb, n_trials)
        results_D['llm_regret'].append(r_llm['avg_regret'])
        results_D['uni_regret'].append(r_uni['avg_regret'])
        results_D['llm_se'].append(r_llm['se_regret'])
        results_D['uni_se'].append(r_uni['se_regret'])
        print(f'  Delta={d:.2f}: LLM regret={r_llm["avg_regret"]:.4f}±{r_llm["se_regret"]:.4f} '
              f'| Uni regret={r_uni["avg_regret"]:.4f}±{r_uni["se_regret"]:.4f}')

    # Experiment 3: Regret ratio vs predicted
    print(f'\n--- Experiment 3: Regret ratio vs I_LLM prediction ---')
    # Compute I_LLM from cached priors
    logZ = np.log2(N_ACTIONS)
    # Cross-entropy H(P*, Q_LLM) approximated by -log2 Q_LLM(optimal)
    H_cross = -np.mean([np.log2(max(LLM_PRIORS[i].get('A', 0.01), 0.01)) for i in range(3)])
    I_LLM = logZ - H_cross
    print(f'  log|Z| = {logZ:.3f} bits')
    print(f'  H(P*, Q_LLM) ~ {H_cross:.3f} bits')
    print(f'  I_LLM ~ {I_LLM:.3f} bits')

    # Predicted regret ratio
    if I_LLM > 0 and I_LLM < logZ:
        predicted_ratio = np.sqrt(1 - I_LLM / logZ)
    else:
        predicted_ratio = 1.0
    print(f'  Predicted regret ratio (LLM/Uni): {predicted_ratio:.3f}')

    # Observed ratio at moderate T
    T_moderate = 30
    r_llm_obs = run_regret_experiment(LLM_PRIORS[0], T_moderate, pg, pb, 500)
    r_uni_obs = run_regret_experiment(UNI_PRIOR, T_moderate, pg, pb, 500)
    observed_ratio = (r_llm_obs['avg_regret'] + 0.001) / max(r_uni_obs['avg_regret'], 0.001)
    print(f'  Observed regret ratio at T=30: {observed_ratio:.3f}')
    print(f'  Match: {abs(predicted_ratio - observed_ratio) < 0.2}')

    # Save
    os.makedirs('results', exist_ok=True)
    output = {
        'regret_vs_T': results_T,
        'regret_vs_Delta': results_D,
        'I_LLM': I_LLM,
        'logZ': logZ,
        'H_cross': H_cross,
        'predicted_ratio': predicted_ratio,
        'observed_ratio': observed_ratio,
        'llm_fit_slope': llm_fit[0],
        'uni_fit_slope': uni_fit[0],
        'slope_ratio': llm_fit[0] / max(uni_fit[0], 0.0001),
        'pg': pg, 'pb': pb, 'Delta': pg - pb
    }
    json.dump(output, open('results/regret_scaling.json', 'w'), indent=2)
    print(f'\nSaved to results/regret_scaling.json')
    print('Done.')


if __name__ == '__main__':
    main()
