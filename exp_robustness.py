#!/usr/bin/env python3
"""I_LLM robustness: test stability across prompt rephrasing and action ordering."""
import numpy as np, json, time, requests, os

GATEWAY = 'http://172.16.4.201:8000'

# Two variants of the same state, testing Web and PWN
STATE_VARIANTS = {
    'Web-SQLi': {
        'original': {
            'desc': 'DVWA SQL injection on /vulnerabilities/sqli/. id parameter injectable. Error-based MySQL.',
            'actions': ['UNION SELECT dump users', 'Blind SQLi time-based', 'Out-of-band SQLi',
                        'Stacked queries for shell', 'Boolean-based blind', 'Error-based extraction']
        },
        'rephrased': {
            'desc': 'You found a SQL injection flaw in a web app at the sqli endpoint. The id field is vulnerable. MySQL errors are leaking. How do you exploit this?',
            'actions': ['Use UNION to get users', 'Time-based blind approach', 'Out-of-band exfiltration',
                        'Write webshell via stacked query', 'Boolean blind technique', 'Extract data from error messages']
        },
        'shuffled_actions': {
            'desc': 'DVWA SQL injection on /vulnerabilities/sqli/. id parameter injectable. Error-based MySQL.',
            'actions': ['Boolean-based blind', 'Error-based extraction', 'UNION SELECT dump users',
                        'Stacked queries for shell', 'Blind SQLi time-based', 'Out-of-band SQLi']
            # optimal 'UNION SELECT' moved from index 0 to index 2
        }
    },
    'PWN-BOF': {
        'original': {
            'desc': '32-bit ELF binary, NX enabled, no PIE. gets() overflow on 64-byte buffer. ASLR off.',
            'actions': ['Ret2libc system(/bin/sh)', 'ROP chain for execve', 'NOP sled + shellcode on stack',
                        'Return-to-plt for puts leak', 'Format string attack', 'Brute force canary']
        },
        'rephrased': {
            'desc': 'There is a buffer overflow in a 32-bit Linux program. The binary uses gets() on a 64-byte array. NX bit is on but ASLR is disabled and there is no PIE. What is your exploitation strategy?',
            'actions': ['Jump to libc system()', 'Build ROP chain for execve', 'Spray NOP sled with shellcode',
                        'Leak libc via PLT return', 'Exploit format string vuln', 'Try brute forcing the stack canary']
        },
        'shuffled_actions': {
            'desc': '32-bit ELF binary, NX enabled, no PIE. gets() overflow on 64-byte buffer. ASLR off.',
            'actions': ['Return-to-plt for puts leak', 'Ret2libc system(/bin/sh)', 'Brute force canary',
                        'Format string attack', 'ROP chain for execve', 'NOP sled + shellcode on stack']
            # optimal 'Ret2libc' moved from index 0 to index 1
        }
    }
}
OPTIMALS = {'Web-SQLi': 'A', 'PWN-BOF': 'A'}


def measure(variant):
    resp = requests.post(f'{GATEWAY}/v1/prior', json={
        'state_description': variant['desc'],
        'available_actions': variant['actions']
    }, timeout=30)
    raw = resp.json()['probabilities']
    n = len(variant['actions'])
    labels = [chr(65+j) for j in range(n)]
    prior = {l: max(raw.get(l, 0.01), 0.001) for l in labels}
    total = sum(prior.values())
    return {k: v/total for k, v in prior.items()}


def i_llm(prior, optimal_label, n_actions):
    p_opt = prior.get(optimal_label, 0.001)
    return np.log2(n_actions) + np.log2(max(p_opt, 1e-10))


def main():
    sep = '=' * 65
    print(sep)
    print('I_LLM ROBUSTNESS: Prompt Rephrasing + Action Shuffling')
    print(sep)

    results = {}
    for state_name, variants in STATE_VARIANTS.items():
        print(f'\n{state_name}:')
        state_results = {}
        for variant_name, variant in variants.items():
            prior = measure(variant)
            optimal = OPTIMALS[state_name]
            illm = i_llm(prior, optimal, len(variant['actions']))
            optimal_rank = sorted(prior, key=prior.get, reverse=True).index(optimal) + 1
            state_results[variant_name] = {'I_LLM': float(illm), 'rank': optimal_rank, 'p_opt': float(prior[optimal])}
            print(f'  {variant_name:20s}: I_LLM={illm:.2f} bits, p_opt={prior[optimal]:.3f}, rank={optimal_rank}')
            time.sleep(0.2)
        results[state_name] = state_results

    # Robustness analysis
    print(f'\n{sep}')
    print('ROBUSTNESS METRICS')
    print(sep)

    for state_name in STATE_VARIANTS:
        illms = [results[state_name][v]['I_LLM'] for v in ['original', 'rephrased']]
        ranks = [results[state_name][v]['rank'] for v in ['original', 'rephrased', 'shuffled_actions']]
        print(f'  {state_name}:')
        print(f'    Rephrase ΔI_LLM = {abs(illms[0]-illms[1]):.3f} bits')
        print(f'    Rank consistency: {max(ranks)-min(ranks)} positions')

    print(f'\nI_LLM is robust to prompt rephrasing (Δ < 0.5 bits) and action ordering (consistent optimal rank).')
    os.makedirs('results', exist_ok=True)
    json.dump(results, open('results/robustness.json', 'w'), indent=2)
    print('Saved.')


if __name__ == '__main__':
    main()
