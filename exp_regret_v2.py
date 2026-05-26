#!/usr/bin/env python3
"""Regret scaling experiment v2 — proper Bayesian regret measurement.

Bayesian regret = E[sum_{t=1}^T (mu(a^*) - mu(a_t))]
where a^* is the optimal arm with mean mu(a^*) = p_g,
and suboptimal arms have mean mu(a) = p_b.

We measure cumulative regret over T pulls and fit sqrt(T) scaling.
"""
import numpy as np
import json, os, time

N_ACTIONS = 10
LABELS = list(range(N_ACTIONS))  # 0 = optimal arm


def ts_mcts_step(prior, T, pg, pb, R=3, lam=0.05):
    """Single TS run. Returns cumulative regret (sum of expected reward gaps)."""
    alpha = {a: 1.0 for a in LABELS}
    beta = {a: 1.0 for a in LABELS}
    cum_regret = 0.0
    n_correct_pulls = 0
    n_total = 0

    for retry in range(R):
        for t in range(T):
            n_total += 1
            samples = {}
            for a in LABELS:
                samples[a] = np.random.beta(alpha[a], beta[a]) + lam * prior.get(a, 1.0/N_ACTIONS)
            chosen = max(samples, key=samples.get)

            # Instantaneous regret: expected reward gap
            if chosen == 0:  # optimal arm
                inst_regret = 0.0
                n_correct_pulls += 1
            else:  # suboptimal arm
                inst_regret = pg - pb  # mu(a^*) - mu(a)

            cum_regret += inst_regret

            # Observe noisy reward
            true_p = pg if chosen == 0 else pb
            reward = np.random.random() < true_p
            if reward:
                alpha[chosen] += 1.0
            else:
                beta[chosen] += 1.0

        # Check if we found the optimal arm
        best = max(LABELS, key=lambda a: alpha[a] / (alpha[a] + beta[a]))
        if best == 0:
            break  # Found optimal, stop retrying
        # Penalize
        beta[best] += 2.0

    return cum_regret, n_correct_pulls, n_total


def run_trials(prior, T, pg, pb, n_trials=300, R=3):
    """Run many trials and compute average regret and success rate."""
    regrets = []
    correct_rates = []

    for _ in range(n_trials):
        cum_reg, n_correct, n_total = ts_mcts_step(prior, T, pg, pb, R)
        regrets.append(cum_reg)
        correct_rates.append(n_correct / max(n_total, 1))

    return {
        'mean_cum_regret': float(np.mean(regrets)),
        'se_cum_regret': float(np.std(regrets) / np.sqrt(n_trials)),
        'mean_correct_rate': float(np.mean(correct_rates)),
        'se_correct_rate': float(np.std(correct_rates) / np.sqrt(n_trials)),
        'n_trials': n_trials
    }


def main():
    sep = '=' * 70
    print(sep)
    print('REGRET SCALING EXPERIMENT v2')
    print('Measuring cumulative Bayesian regret: E[sum (mu(a*) - mu(a_t))]')
    print(sep)

    # Realistic LLM-inspired priors from I_LLM measurements
    # Crypto: I_LLM ~ 1.57 bits (strong prior)
    # Web: I_LLM ~ 0.81 bits (moderate prior)
    # PWN: I_LLM ~ 0.16 bits (weak prior)
    # We construct priors with these I_LLM values

    def make_prior(p_opt, K=N_ACTIONS):
        """Create a prior distribution with given P(optimal)."""
        prior = {0: p_opt}
        remaining = (1.0 - p_opt) / (K - 1)
        for a in range(1, K):
            prior[a] = remaining
        return prior

    # Priors corresponding to measured I_LLM values
    # I_LLM = log2(K) - H_cross, H_cross = -log2(p_opt)
    # So p_opt = 2^{-(log2(K) - I_LLM)} = K / 2^{I_LLM}... no
    # I_LLM = log2(K) - (-log2(p_opt)) = log2(K) + log2(p_opt) = log2(K * p_opt)
    # So p_opt = 2^{I_LLM} / K
    def i_llm_to_p_opt(i_llm, K=N_ACTIONS):
        return (2 ** i_llm) / K

    UNI_PRIOR = {a: 1.0 / N_ACTIONS for a in LABELS}

    priors_to_test = {
        'Uniform': UNI_PRIOR,
        'Strong (Crypto-like, I≈1.6)': make_prior(i_llm_to_p_opt(1.6)),
        'Moderate (Web-like, I≈0.8)': make_prior(i_llm_to_p_opt(0.8)),
        'Weak (PWN-like, I≈0.2)': make_prior(i_llm_to_p_opt(0.2)),
    }

    # Experiment 1: Cumulative regret vs T
    T_vals = [5, 10, 20, 30, 50, 100, 200]
    pg, pb = 0.55, 0.30  # Delta = 0.25 (moderate noise)
    n_trials = 200

    print(f'\n--- Experiment 1: Cumulative Regret vs T (Delta={pg-pb:.2f}) ---')
    print(f'{"T":>5} {"Uniform":>15} {"Strong":>15} {"Moderate":>15} {"Weak":>15}')
    print('-' * 68)

    regret_data = {name: {'T': [], 'regret': [], 'se': [], 'correct': []}
                   for name in priors_to_test}

    for T in T_vals:
        row = f'{T:>5}'
        for name, prior in priors_to_test.items():
            r = run_trials(prior, T, pg, pb, n_trials)
            regret_data[name]['T'].append(T)
            regret_data[name]['regret'].append(r['mean_cum_regret'])
            regret_data[name]['se'].append(r['se_cum_regret'])
            regret_data[name]['correct'].append(r['mean_correct_rate'])
            row += f' {r["mean_cum_regret"]:>12.4f}±{r["se_cum_regret"]:.4f}'
        print(row)

    # Fit sqrt(T) scaling
    sqrt_T = np.sqrt(T_vals)
    print(f'\n--- Sqrt(T) Scaling Fits ---')
    for name in priors_to_test:
        regrets = regret_data[name]['regret']
        # Regret should be linear in sqrt(T): regret = a*sqrt(T) + b
        fit = np.polyfit(sqrt_T, regrets, 1)
        r2 = 1 - np.sum((np.array(regrets) - (fit[0]*sqrt_T + fit[1]))**2) / np.sum((np.array(regrets) - np.mean(regrets))**2)
        print(f'  {name}: regret = {fit[0]:.4f}*sqrt(T) + {fit[1]:.4f} (R²={r2:.3f})')

    # Experiment 2: Regret vs Delta at fixed T
    T_fixed = 50
    Delta_vals = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40]
    pg_vals = [0.50 + d/2 for d in Delta_vals]
    pb_vals = [0.50 - d/2 for d in Delta_vals]

    print(f'\n--- Experiment 2: Regret vs Delta (T={T_fixed}) ---')
    print(f'{"Delta":>7} {"Uniform":>15} {"Moderate":>15} {"Weak":>15}')
    print('-' + '-'*52)

    delta_data = {'Delta': Delta_vals}

    for d, pg, pb in zip(Delta_vals, pg_vals, pb_vals):
        u = run_trials(UNI_PRIOR, T_fixed, pg, pb, n_trials)
        m = run_trials(priors_to_test['Moderate (Web-like, I≈0.8)'], T_fixed, pg, pb, n_trials)
        w = run_trials(priors_to_test['Weak (PWN-like, I≈0.2)'], T_fixed, pg, pb, n_trials)
        print(f'  {d:>5.2f}  {u["mean_cum_regret"]:>12.4f}±{u["se_cum_regret"]:.4f}  '
              f'{m["mean_cum_regret"]:>12.4f}±{m["se_cum_regret"]:.4f}  '
              f'{w["mean_cum_regret"]:>12.4f}±{w["se_cum_regret"]:.4f}')

    # Experiment 3: I_LLM-predicted vs observed regret ratio
    print(f'\n--- Experiment 3: Theory Validation ---')
    logZ = np.log2(N_ACTIONS)
    T_ref = 50
    uni_ref = run_trials(UNI_PRIOR, T_ref, pg, pb, 500)

    for name, prior in priors_to_test.items():
        if name == 'Uniform':
            continue
        r = run_trials(prior, T_ref, pg, pb, 500)
        # Extract I_LLM from prior
        p_opt = prior[0]
        H_cross = -np.log2(max(p_opt, 1e-10))
        I_LLM = logZ - H_cross
        predicted_ratio = np.sqrt(1 - I_LLM / logZ) if 0 < I_LLM < logZ else 1.0
        observed_ratio = (r['mean_cum_regret'] + 0.0001) / max(uni_ref['mean_cum_regret'], 0.0001)

        print(f'  {name}: I_LLM={I_LLM:.2f} bits | Predicted ratio={predicted_ratio:.3f} | '
              f'Observed ratio={observed_ratio:.3f} | Match={abs(predicted_ratio-observed_ratio)<0.15}')

    os.makedirs('results', exist_ok=True)
    output = {
        'regret_vs_T': {name: data for name, data in regret_data.items()},
        'delta_data': delta_data,
        'pg': pg, 'pb': pb, 'Delta': pg - pb,
        'n_trials': n_trials
    }
    json.dump(output, open('results/regret_scaling_v2.json', 'w'), indent=2)
    print('\nSaved to results/regret_scaling_v2.json')
    print('Done.')


if __name__ == '__main__':
    main()
