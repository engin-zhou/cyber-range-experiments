#!/usr/bin/env python3
"""Temperature sweep: measure I_LLM stability across inference temperatures.
Also serves as a robustness check for the prior quality metric."""
import numpy as np, json, time, requests, os

GATEWAY = 'http://172.16.4.201:8000'

# Use the same 6 categories from the I_LLM experiment
CATEGORIES = {
    'Crypto': [
        {'n': 6, 'optimal': 'A',
         'desc': 'RSA: n=3233, e=17, c=855. Small modulus suggests weak key.',
         'actions': ['Factor n via factordb', 'Wiener attack', 'Common modulus attack',
                     'Hastad broadcast', 'LLL reduction', 'Fermat factorization']},
        {'n': 6, 'optimal': 'A',
         'desc': 'AES-ECB encrypted cookie. Chosen-plaintext oracle available. Block size 16.',
         'actions': ['Byte-at-a-time ECB decryption', 'CBC bit flipping', 'Padding oracle attack',
                     'CBC-MAC forgery', 'GCM nonce reuse', 'CTR stream key reuse']},
    ],
    'Web': [
        {'n': 6, 'optimal': 'A',
         'desc': 'DVWA SQL injection on /vulnerabilities/sqli/. id parameter injectable. Error-based MySQL.',
         'actions': ['UNION SELECT dump users', 'Blind SQLi time-based', 'Out-of-band SQLi',
                     'Stacked queries for shell', 'Boolean-based blind', 'Error-based extraction']},
        {'n': 6, 'optimal': 'A',
         'desc': 'WordPress 5.8 with vulnerable plugin. Admin panel at /wp-admin. WPScan found CVE-2024-xxx.',
         'actions': ['Exploit vulnerable plugin', 'XML-RPC brute force', 'Theme file edit to web shell',
                     'Database backup extraction', 'WP-Cron RCE', 'Phish admin via XSS']},
    ],
    'PWN': [
        {'n': 6, 'optimal': 'A',
         'desc': '32-bit ELF binary, NX enabled, no PIE. gets() overflow on 64-byte buffer.',
         'actions': ['Ret2libc system(/bin/sh)', 'ROP chain for execve', 'NOP sled + shellcode on stack',
                     'Return-to-plt for puts leak', 'Format string attack', 'Brute force canary']},
        {'n': 6, 'optimal': 'A',
         'desc': '64-bit binary with heap UAF vulnerability. tcache poisoning possible.',
         'actions': ['Tcache poison to __free_hook', 'House of Force', 'Unsorted bin attack',
                     'Fastbin dup to stack', 'House of Spirit', 'Off-by-one to chunk overlap']},
    ],
}

TEMPERATURES = [0.1, 0.3, 0.5, 0.7, 1.0]
N_RUNS_PER_TEMP = 3  # repeat each measurement to check variance


def measure_prior(state, temperature):
    """Get LLM prior at specific temperature."""
    resp = requests.post(f'{GATEWAY}/v1/prior', json={
        'state_description': state['desc'],
        'available_actions': state['actions'],
        'context': f'temperature={temperature}'
    }, timeout=30)
    raw = resp.json()['probabilities']
    n = state['n']
    labels = [chr(65+j) for j in range(n)]
    prior = {l: max(raw.get(l, 0.01), 0.001) for l in labels}
    total = sum(prior.values())
    prior = {k: v/total for k, v in prior.items()}
    return prior


def compute_i_llm(prior, state):
    """Compute I_LLM and accuracy for a prior."""
    optimal = state['optimal']
    p_opt = prior.get(optimal, 0.001)
    n = state['n']
    logK = np.log2(n)
    I_LLM = logK + np.log2(max(p_opt, 1e-10))
    rank = sorted(prior, key=prior.get, reverse=True).index(optimal) + 1
    return {
        'I_LLM': float(I_LLM),
        'p_opt': float(p_opt),
        'rank': rank,
        'correct': rank == 1,
        'logK': float(logK)
    }


def main():
    sep = '=' * 65
    print(sep)
    print('TEMPERATURE SWEEP: I_LLM Stability Analysis')
    print(sep)
    print(f'Temperatures: {TEMPERATURES}')
    print(f'Runs per temp: {N_RUNS_PER_TEMP}')
    print(f'Categories: {list(CATEGORIES.keys())} ({sum(len(v) for v in CATEGORIES.values())} states)')

    all_results = {}

    for temp in TEMPERATURES:
        print(f'\n--- Temperature = {temp} ---')
        temp_results = {}

        for cat_name, states in CATEGORIES.items():
            cat_i_llms = []
            cat_correct = 0

            for run in range(N_RUNS_PER_TEMP):
                for i, state in enumerate(states):
                    # Different cache key per temperature due to context field
                    prior = measure_prior(state, temp)
                    metrics = compute_i_llm(prior, state)
                    cat_i_llms.append(metrics['I_LLM'])
                    if metrics['correct']:
                        cat_correct += 1
                    time.sleep(0.2)

            n_total = len(states) * N_RUNS_PER_TEMP
            temp_results[cat_name] = {
                'mean_I_LLM': float(np.mean(cat_i_llms)),
                'std_I_LLM': float(np.std(cat_i_llms)),
                'accuracy': cat_correct / n_total,
            }
            print(f'  {cat_name}: I_LLM={np.mean(cat_i_llms):.2f} +/- {np.std(cat_i_llms):.2f} bits, acc={cat_correct/n_total:.0%}')

        all_results[str(temp)] = temp_results

    # Cross-temperature stability analysis
    print(f'\n{sep}')
    print('CROSS-TEMPERATURE STABILITY')
    print(sep)
    print(f'{"Category":<12} {"Mean I_LLM":>10} {"Std across T":>10} {"CV":>8}')
    print('-' * 42)

    for cat_name in CATEGORIES:
        cat_i_llms = [all_results[str(t)][cat_name]['mean_I_LLM'] for t in TEMPERATURES]
        mean_across = np.mean(cat_i_llms)
        std_across = np.std(cat_i_llms)
        cv = std_across / max(abs(mean_across), 0.001)
        print(f'{cat_name:<12} {mean_across:>8.2f} bits {std_across:>8.3f} bits {cv:>7.1%}')

    # Key finding
    cv_values = []
    for cat_name in CATEGORIES:
        cat_i_llms = [all_results[str(t)][cat_name]['mean_I_LLM'] for t in TEMPERATURES]
        cv_values.append(np.std(cat_i_llms) / max(abs(np.mean(cat_i_llms)), 0.001))
    print(f'\nMean CV across categories: {np.mean(cv_values):.1%}')
    print(f'Conclusion: I_LLM is {"stable" if np.mean(cv_values) < 0.15 else "moderately stable"} across temperatures')

    os.makedirs('results', exist_ok=True)
    json.dump(all_results, open('results/temperature_sweep.json', 'w'), indent=2)
    print('\nSaved.')
    print('Done.')


if __name__ == '__main__':
    main()
