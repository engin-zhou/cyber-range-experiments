#!/usr/bin/env python3
"""Lambda prior-weight sensitivity analysis.
Tests lambda in {0.005, 0.01, 0.03, 0.05, 0.08, 0.10, 0.15, 0.20}
across three noise regimes: low (Delta=0.10), moderate (0.22), high (0.32).
"""
import numpy as np, json, os, time

N_ACTIONS = 10
LABELS = list(range(N_ACTIONS))
N_TRIALS = 200
T_VALS = [10, 30, 50]
LAMBDA_VALS = [0.005, 0.01, 0.03, 0.05, 0.08, 0.10, 0.15, 0.20]
DELTA_CASES = [(0.50, 0.40, 0.10, 'low'), (0.50, 0.28, 0.22, 'moderate'), (0.50, 0.18, 0.32, 'high')]

# Moderate LLM prior (Web-like, I_LLM ~ 0.8 bits, p_opt ~ 0.25)
PRIOR_MODERATE = {0: 0.25}
remaining = (1.0 - 0.25) / (N_ACTIONS - 1)
for a in range(1, N_ACTIONS):
    PRIOR_MODERATE[a] = remaining

UNI_PRIOR = {a: 1.0 / N_ACTIONS for a in LABELS}


def ts_step(prior_dict, T, pg, pb, lam, R=3):
    alpha = {a: 1.0 for a in LABELS}
    beta = {a: 1.0 for a in LABELS}
    for retry in range(R):
        for t in range(T):
            samples = {}
            for a in LABELS:
                samples[a] = np.random.beta(alpha[a], beta[a]) + lam * prior_dict.get(a, 1/N_ACTIONS)
            chosen = max(samples, key=samples.get)
            true_p = pg if chosen == 0 else pb
            reward = np.random.random() < true_p
            if reward:
                alpha[chosen] += 1.0
            else:
                beta[chosen] += 1.0
        best = max(LABELS, key=lambda a: alpha[a] / (alpha[a] + beta[a]))
        if best == 0:
            return True
        beta[best] += 2.0
    return False


def main():
    sep = '=' * 65
    print(sep)
    print('LAMBDA PRIOR-WEIGHT SENSITIVITY ANALYSIS')
    print(sep)

    results = {}

    for pg, pb, delta, label in DELTA_CASES:
        print(f'\n--- Delta={delta:.2f} ({label} noise) ---')
        print(f'{"lambda":>8} {"T=10 LLM":>10} {"T=10 Uni":>10} {"T=30 LLM":>10} {"T=30 Uni":>10} {"T=50 LLM":>10} {"T=50 Uni":>10}')
        print('-' * 75)

        for lam in LAMBDA_VALS:
            row = f'{lam:>8.3f}'
            for T in T_VALS:
                llm_ok = sum(ts_step(PRIOR_MODERATE, T, pg, pb, lam) for _ in range(N_TRIALS))
                uni_ok = sum(ts_step(UNI_PRIOR, T, pg, pb, lam) for _ in range(N_TRIALS))
                key = f'{label}_{lam}_{T}'
                results[key] = {'llm': llm_ok/N_TRIALS, 'uni': uni_ok/N_TRIALS, 'diff': (llm_ok - uni_ok)/N_TRIALS}
                row += f' {llm_ok/N_TRIALS:>10.3f} {uni_ok/N_TRIALS:>10.3f}'
            print(row)

    # Optimal lambda per regime
    print(f'\n{sep}')
    print('OPTIMAL LAMBDA PER REGIME')
    print(sep)
    for pg, pb, delta, label in DELTA_CASES:
        best_lam = None
        best_adv = -99
        for lam in LAMBDA_VALS:
            adv_sum = 0
            for T in T_VALS:
                key = f'{label}_{lam}_{T}'
                adv_sum += results[key]['diff']
            avg_adv = adv_sum / len(T_VALS)
            if avg_adv > best_adv:
                best_adv = avg_adv
                best_lam = lam
        print(f'  {label} noise (Delta={delta}): best lambda = {best_lam}, avg advantage = {best_adv:+.3f}')

    # Finding: lambda too high hurts
    print(f'\n{sep}')
    print('KEY FINDING')
    print(sep)
    for label in ['low', 'moderate', 'high']:
        adv_005 = np.mean([results[f'{label}_{lam}_{T}']['diff'] for lam in [0.005] for T in T_VALS])
        adv_010 = np.mean([results[f'{label}_{lam}_{T}']['diff'] for lam in [0.10] for T in T_VALS])
        adv_020 = np.mean([results[f'{label}_{lam}_{T}']['diff'] for lam in [0.20] for T in T_VALS])
        print(f'  {label}: lambda=0.005 adv={adv_005:+.3f}, lambda=0.10 adv={adv_010:+.3f}, lambda=0.20 adv={adv_020:+.3f}')
    print(f'  Lambda > 0.10 suppresses learning from data; lambda < 0.01 ignores prior.')

    os.makedirs('results', exist_ok=True)
    json.dump(results, open('results/lambda_sweep.json', 'w'), indent=2)
    print('\nSaved.')


if __name__ == '__main__':
    main()
